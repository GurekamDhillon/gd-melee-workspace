// Decompile every ACMD script of an Ultimate fighter module (lua2cpp_<fighter>.nro) to C text.
//
//   analyzeHeadless <project dir> <name> -process <nro> -noanalysis \
//       -scriptPath <dir with this file> -postScript DumpAcmd.java <out dir>
//   (Ghidra rejects project paths with an apostrophe; the .bat splits arguments on commas.)
//
// A fighter's move scripts are registered at agent creation, not exported by name:
// lua2cpp::create_agent_{fighter,weapon}_animcmd_{game,effect,sound,expression}[_share]_<fighter>
// switches on the agent's Hash40 (the fighter, or one of its weapons/articles) and, per agent,
// calls lib::L2CAgent::sv_set_function_hash(this, <script function>, <Hash40 of the script name>).
// This reads those registrations from each create_agent function's decompiled text, defines a
// function at every registered address, decompiles it, and writes
//   <out dir>/<kind>/<agent hash>__<script hash>.c   (first line: addresses and hashes)
// plus <out dir>/index.tsv. Hashes are resolved to names by ports/ir/tools/acmd_parse.py.
//@category Ultimate

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

import java.io.File;
import java.io.PrintWriter;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class DumpAcmd extends GhidraScript {
    private static final Pattern CREATE = Pattern.compile(
        "create_agent_(fighter|weapon)_animcmd_(game|effect|sound|expression)(_share)?_\\w+");
    private static final Pattern AGENT = Pattern.compile("==\\s*(0x[0-9a-f]+)\\)");
    private static final Pattern REG = Pattern.compile(
        "sv_set_function_hash\\(\\w+,&?(?:DAT|FUN|LAB)_([0-9a-f]+),(0x[0-9a-f]+)\\)");
    private static final Pattern BODY = Pattern.compile("(?:func_0x0*|FUN_)([0-9a-f]{8,})\\(");
    // "func_0x..." until Ghidra has defined the helper, "FUN_..." after (the project is saved)
    private static final Pattern HELPER = Pattern.compile("(?:func_0x0*|FUN_)([0-9a-f]{8,})\\(param_2,");

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        File out = new File(args[0]);
        out.mkdirs();
        DecompInterface dec = new DecompInterface();
        dec.openProgram(currentProgram);
        int n = 0, failed = 0;
        java.util.Set<String> helpers = new java.util.HashSet<>();
        try (PrintWriter index = new PrintWriter(new File(out, "index.tsv"), "UTF-8")) {
            index.println("kind\tshare\towner\tagent_hash\tscript_hash\taddress\tstatus");
            for (Function cf : currentProgram.getFunctionManager().getFunctions(true)) {
                Matcher cm = CREATE.matcher(cf.getName(true));
                if (!cm.find()) continue;
                String owner = cm.group(1), kind = cm.group(2), share = cm.group(3) != null ? "share" : "";
                DecompileResults cr = dec.decompileFunction(cf, 600, monitor);
                if (cr == null || !cr.decompileCompleted()) {
                    printerr("cannot decompile " + cf.getName(true));
                    continue;
                }
                String agent = "unknown";
                for (String line : cr.getDecompiledFunction().getC().split("\n")) {
                    Matcher am = AGENT.matcher(line);
                    if (am.find()) agent = am.group(1);
                    Matcher rm = REG.matcher(line);
                    if (!rm.find()) continue;
                    Address at = toAddr(Long.parseLong(rm.group(1), 16));
                    Function f = getFunctionAt(at);
                    if (f == null) f = createFunction(at, null);
                    String status = "ok";
                    File dir = new File(out, kind);
                    dir.mkdirs();
                    try (PrintWriter w = new PrintWriter(new File(dir, agent + "__" + rm.group(2) + ".c"), "UTF-8")) {
                        w.println("// " + owner + " " + kind + (share.isEmpty() ? "" : " share") + " agent " + agent
                                  + " script " + rm.group(2) + " @ " + at);
                        DecompileResults r = f == null ? null : dec.decompileFunction(f, 300, monitor);
                        if (r != null && r.decompileCompleted()) {
                            String wrapper = r.getDecompiledFunction().getC();
                            w.println(wrapper);
                            // The registered function is a wrapper (Variadic::get_format, then the
                            // script body on an L2CValue); the body is the first call to a code
                            // address Ghidra had not defined. Define it and decompile it too.
                            Matcher bm = BODY.matcher(wrapper);
                            Address ba = null;
                            while (bm.find()) {       // the first call that is not the wrapper itself
                                Address c = toAddr(Long.parseLong(bm.group(1), 16));
                                if (!c.equals(at)) { ba = c; break; }
                            }
                            if (ba != null) {
                                Function bf = getFunctionAt(ba);
                                if (bf == null) bf = createFunction(ba, null);
                                DecompileResults br = bf == null ? null : dec.decompileFunction(bf, 600, monitor);
                                w.println("// BODY @ " + ba);
                                if (br != null && br.decompileCompleted()) {
                                    String body = br.getDecompiledFunction().getC();
                                    w.println(body);
                                    // ACMD macros (ATTACK, EFFECT...) are compiled as local helper
                                    // functions called with the argument L2CValues: decompile each
                                    // helper once so the parser can name it by what it calls.
                                    Matcher hm = HELPER.matcher(body);
                                    while (hm.find()) {
                                        String ha = hm.group(1);
                                        if (!helpers.add(ha)) continue;
                                        Address haddr = toAddr(Long.parseLong(ha, 16));
                                        Function hf = getFunctionAt(haddr);
                                        if (hf == null) hf = createFunction(haddr, null);
                                        DecompileResults hr = hf == null ? null : dec.decompileFunction(hf, 300, monitor);
                                        File hdir = new File(out, "helpers");
                                        hdir.mkdirs();
                                        try (PrintWriter hw = new PrintWriter(new File(hdir, ha + ".c"), "UTF-8")) {
                                            hw.println(hr != null && hr.decompileCompleted()
                                                       ? hr.getDecompiledFunction().getC() : "// DECOMPILE FAILED");
                                        }
                                    }
                                } else {
                                    status = "body_failed";
                                    failed++;
                                    w.println("// BODY DECOMPILE FAILED");
                                }
                            } else {
                                status = "no_body";
                            }
                        } else {
                            status = "failed";
                            failed++;
                            w.println("// DECOMPILE FAILED");
                        }
                    }
                    index.println(kind + "\t" + share + "\t" + owner + "\t" + agent + "\t" + rm.group(2) + "\t" + at + "\t" + status);
                    n++;
                }
            }
        }
        dec.dispose();
        println("DumpAcmd: " + n + " scripts, " + failed + " failed -> " + out);
    }
}
