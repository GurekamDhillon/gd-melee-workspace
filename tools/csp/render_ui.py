"""Render a built Geno package's UI through local CSProject + Blender 3.5.1.

python tools/csp/render_ui.py --project ports/goku-xv2 --costume all --pose Wait:0
Fetching is explicit (fetch_csproject.py). All images, inventories and jobs
remain in _build. Declarations are published after all conversions succeed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import time
import uuid

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.csp.fetch_csproject import load_tools
from tools.csp.outputs import OUTPUTS, camera_outputs, fit_rgba, postprocess, merge_presentation, validate_gxtex
from tools.csp.project import ROOT, generated_path, confined_path, load_project, workspace_root


def convert_png(source, destination, spec, *, tool=None):
    if tool is None:
        game = Path(os.environ.get('GW_MELEE', workspace_root() / 'melee'))
        tool = game / 'pc/tools/png2gx.py'
    tool = Path(tool)
    if not tool.is_file():
        raise ValueError('Missing game pc/tools/png2gx.py; set GW_MELEE: ' + str(tool))
    # png2gx tiles in 4x4 blocks and cannot read past the image edge, so an odd retail
    # size (52x74) is converted from a transparent canvas padded to a multiple of 4 and
    # the GXTX header is then patched back to the true size (tile data stays padded,
    # as retail textures are).
    from PIL import Image
    width, height = spec.size
    with Image.open(source) as image:
        if image.size != (width, height):
            raise ValueError('%s is %s, expected %s' % (source, image.size, spec.size))
        padded = (-(-width // 4) * 4, -(-height // 4) * 4)
        canvas = Image.new('RGBA', padded, (0, 0, 0, 0))
        canvas.paste(image.convert('RGBA'), (0, 0))
    padded_png = Path(str(destination) + '.pad.png')
    try:
        canvas.save(padded_png)
        subprocess.run([sys.executable, str(tool), str(padded_png), str(destination),
                        '--format', spec.format, '--allow-odd-size'], check=True)
    finally:
        padded_png.unlink(missing_ok=True)
    data = bytearray(Path(destination).read_bytes())
    data[12:20] = struct.pack('>II', width, height)
    Path(destination).write_bytes(bytes(data))
    validate_gxtex(destination, spec)


def process_views(views, destination, effects):
    from PIL import Image
    destination.mkdir(parents=True, exist_ok=True)
    output = {}
    if set(effects) - set(views):
        raise ValueError('Unknown camera in ui_render.effects: ' + repr(set(effects) - set(views)))
    for index, (camera, path) in enumerate(views.items()):
        with Image.open(path) as source:
            family = re.sub(r'[^a-z0-9]', '', camera.lower())
            settings = {}
            if 'stock' in family:
                settings['outline'] = max(1, min(32, round(source.width / 24)))
            elif 'csp' in family:
                settings['shadow'] = (max(1, round(source.width * 2 / 136)), max(1, round(source.height * 2 / 188)))
            settings.update(effects.get(camera, {}))
            image = postprocess(source, **settings)
        target = destination / ('camera-%02d.png' % index)
        image.save(target)
        output[camera] = target
    return output


def publish_package(job, renders, *, convert=None):
    """Stage every view/encoding, then install content-named files and metadata.

    Failure before publication leaves the original geno.json and art untouched.
    A later metadata write failure may leave unused new files; old files survive.
    """
    from PIL import Image
    convert = convert or convert_png
    package = generated_path(job['package'], job['root'])
    document_path = confined_path(package / 'geno.json', package)
    files = confined_path(package / 'files', package)
    before = document_path.read_bytes()
    if job.get('doc_digest') and hashlib.sha256(before).hexdigest() != job['doc_digest']:
        raise RuntimeError('Package changed after preparing the render job; rerun against the current build')
    doc = json.loads(before)
    entry = doc['fighters'][job['entry_index']]
    if len(entry.get('fighter', {}).get('costumes', [{}])) != job['count']:
        raise ValueError('Package costume list changed while rendering')
    rendered, assets = {}, []
    prefix = re.sub(r'[^A-Za-z0-9_]', '_', job['key'])[:20] or 'fighter'
    with tempfile.TemporaryDirectory(prefix='.csp-stage-', dir=package) as temporary:
        stage = Path(temporary)
        def encode(field, image, index):
            spec = OUTPUTS[field]
            stem = 'GnUi_%s_%s_c%03d' % (prefix, field, index)
            png, gx = stage / (stem + '.png'), stage / (stem + '.gxtex')
            fit_rgba(image, spec.size).save(png)
            convert(png, gx, spec)
            validate_gxtex(gx, spec)
            digest = hashlib.sha256(gx.read_bytes()).hexdigest()[:10]
            name = stem + '_' + digest + '.gxtex'
            assets.append((gx, name))
            return name
        for index, views in renders.items():
            index = int(index)
            if len(views) != 9:
                raise ValueError('Expected nine rendered camera outputs for costume ' + str(index))
            mapping = camera_outputs(views, job.get('fields'))
            processed = process_views(views, stage / ('c%03d' % index), job.get('effects', {}))
            rendered[index] = {}
            for field, camera in mapping.items():
                if field == 'icon' and index != 0:
                    continue
                # An automatic zero render repairs absent fallback fields only.
                # Explicitly selecting zero/all replaces every selected field.
                if index == 0 and job.get('fallback_zero_fields') and field not in job['fallback_zero_fields']:
                    continue
                with Image.open(processed[camera]) as image:
                    rendered[index][field] = encode(field, image, index)
        presentation = merge_presentation(entry.get('presentation', {}), rendered, job['count'])
        if job.get('emblem'):
            with Image.open(job['emblem']) as image:
                presentation['emblem'] = encode('emblem', image, 0)
        if document_path.read_bytes() != before:
            raise RuntimeError('Package metadata changed during UI conversion; no declarations published')
        files = confined_path(package / 'files', package)
        files.mkdir(exist_ok=True)
        # Content-named files do not overwrite a previous successful pose's art.
        for source, name in assets:
            destination = confined_path(files / name, files)
            if destination.exists():
                if destination.read_bytes() != source.read_bytes():
                    raise RuntimeError('UI art filename collision: ' + name)
            else:
                os.replace(source, destination)
        for value in presentation.values():
            for name in value if isinstance(value, list) else [value]:
                if not confined_path(files / name, files).is_file():
                    raise ValueError('Presentation would reference a missing file: ' + name)
        entry['presentation'] = presentation
        updated = stage / 'geno.json'
        updated.write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8')
        os.replace(updated, document_path)
    return presentation


def run_blender(tools, arguments, log, *, cancel_file=None):
    command = [tools['blender'], '--background', '--factory-startup', '--python-exit-code', '1',
               '--python', str(ROOT / 'tools/csp/blender_render.py'), '--', *map(str, arguments)]
    env = dict(os.environ, BLENDER_USER_SCRIPTS=tools['scripts'])
    with Path(log).open('w', encoding='utf-8') as output:
        process = subprocess.Popen(command, env=env, stdout=output, stderr=subprocess.STDOUT, text=True)
        try:
            while process.poll() is None:
                if cancel_file is not None and Path(cancel_file).exists():
                    raise RuntimeError('UI render cancelled')
                time.sleep(0.2)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
    if process.returncode:
        tail = Path(log).read_text(encoding='utf-8', errors='replace')[-5000:]
        raise RuntimeError('Blender failed (%s); %s\n%s' % (process.returncode, log, tail))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project', type=Path, help='workbench.json or its directory')
    ap.add_argument('--package', type=Path, help='actual package built; overrides the project plan location')
    ap.add_argument('--fighter', type=Path, help='artist fighter.json used by this build')
    ap.add_argument('--art', type=Path, help='local original .blend/.glb art override')
    ap.add_argument('--costume', default='all', help='zero-based N or all')
    ap.add_argument('--pose', help='workbench row/clip or numeric animation row, followed by :frame')
    ap.add_argument('--retail-scene', type=Path, help='render this local retail CSProject scene instead of original art')
    ap.add_argument('--template', type=Path, help='local template .blend override')
    ap.add_argument('--scene-config', type=Path, help='verified scene/camera/recolor settings JSON')
    ap.add_argument('--emblem', type=Path, help='authored PNG; an omitted emblem declaration is preserved')
    ap.add_argument('--inspect-template', action='store_true', help='write only scene inventory for the lead')
    ap.add_argument('--cancel-file', type=Path, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if not args.inspect_template and not args.project:
        ap.error('--project is required for rendering')
    root = workspace_root()
    try:
        cancel_file = generated_path(args.cancel_file, root) if args.cancel_file else None
        if cancel_file is not None and cancel_file.exists():
            raise RuntimeError('UI render cancelled')
        tools = load_tools(root)
        version = subprocess.run([tools['blender'], '--version'], check=True, capture_output=True, text=True).stdout
        if not version.splitlines() or version.splitlines()[0] != 'Blender 3.5.1':
            raise ValueError('Configured renderer is not exact Blender 3.5.1')
        template = (args.retail_scene or args.template or Path(tools['template'])).resolve()
        if not template.is_file():
            raise ValueError('Missing local template scene: ' + str(template))
        base = generated_path(root / '_build/csp-render', root)
        base.mkdir(parents=True, exist_ok=True)
        if args.inspect_template:
            inventory_path = confined_path(base / 'template-inventory.json', base)
            run_blender(tools, ['--inspect-template', template, '--out', inventory_path], confined_path(base / 'inspect.log', base), cancel_file=cancel_file)
            print('CSProject inventory:', inventory_path)
            return 0
        job = load_project(args.project, root=root, package=args.package, fighter=args.fighter,
                           art=args.art, pose=args.pose, costume=args.costume,
                           retail_scene=args.retail_scene, scene_config=args.scene_config, emblem=args.emblem)
        job['template'], job['scripts'] = str(template), tools['scripts']
        metadata = confined_path(Path(job['package']) / 'geno.json', job['package'])
        job['doc_digest'] = hashlib.sha256(metadata.read_bytes()).hexdigest()
        work = confined_path(base / (re.sub(r'[^A-Za-z0-9_-]', '_', job['key'])[:40] or 'fighter') / uuid.uuid4().hex, base)
        work.mkdir(parents=True)
        renders, scene_reports = {}, []
        # One process per costume bounds Blender datablock memory and prevents
        # a previous recolor/action from leaking into the next render.
        for costume in job['costumes']:
            part = confined_path(work / ('c%03d' % costume['index']), work)
            part.mkdir()
            worker_job = dict(job, costumes=[costume], work=str(part))
            request = confined_path(part / 'job.json', part)
            request.write_text(json.dumps(worker_job, indent=2) + '\n', encoding='utf-8')
            run_blender(tools, ['--job', request], confined_path(part / 'blender.log', part), cancel_file=cancel_file)
            result = json.loads((part / 'renders.json').read_text(encoding='utf-8'))
            renders.update({int(i): paths for i, paths in result['renders'].items()})
            scene_reports.extend(result['scenes'])
            print('Rendered nine cameras for costume', costume['index'])
        if cancel_file is not None and cancel_file.exists():
            raise RuntimeError('UI render cancelled')
        presentation = publish_package(job, renders)
        report = dict(job, work=str(work), scenes=scene_reports, presentation=presentation)
        confined_path(work / 'ui-render.json', work).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print('UI presentation:', json.dumps(presentation))
        print('Render report:', work / 'ui-render.json')
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print('csp render: ' + str(exc), file=sys.stderr)
        print('Prepare tools with: python tools/csp/fetch_csproject.py', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
