#pragma once
// Synthetic fighter project for workbench tests. No disc- or XV2-derived data: names, numbers and
// bone roles are invented. Layout mirrors a port (ports/<id>/): gameplay.json, moves/*.genoasm,
// fidelity.json, workbench.json, and a stand-in for the built package's plan.json.
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QString>

namespace wbtest {
inline void put(const QString &dir, const QString &rel, const QByteArray &data) {
    QFileInfo fi(QDir(dir).filePath(rel));
    QDir().mkpath(fi.absolutePath());
    QFile f(fi.absoluteFilePath());
    if (!f.open(QIODevice::WriteOnly)) qFatal("fixture: cannot write %s", qPrintable(rel));
    f.write(data);
}

inline const char *kGameplay = R"JSON({
  "version": 1,
  "moves": [
    {
      "name": "jab1",
      "motions": [44],
      "tag": "jab",
      "script": "moves/jab1.genoasm",
      "iasa": 18,
      "pick": {"status": "provisional", "clip": "SYN_ATC_002", "crop_start": 9, "startup": 3}
    },
    {
      "name": "dair",
      "motions": [70],
      "tag": "aerial",
      "script": "moves/dair.genoasm",
      "iasa": 36,
      "pick": {"status": "provisional", "clip": "SYN_ATC_007", "crop_start": 2, "startup": 6}
    }
  ],
  "states": []
}
)JSON";

inline const char *kJab = "# synthetic\nPUT ANIM_RATE 1.0\nwait_until 3\n"
    "hitbox slot=0 joint=@HAND_R@ damage=3 size=3.40 x=0.00 y=0.00 z=0.00 angle=361 kbg=50 fkb=0 bkb=8\n"
    "wait 2\nclear_hitboxes\nwait_until 18\niasa\n";

inline const char *kDair = "# synthetic\nPUT ANIM_RATE 1.0\nwait_until 6\n"
    "hitbox slot=0 joint=@FOOT_L@ damage=14 size=2.80 x=0.00 y=0.00 z=0.00 angle=270 kbg=90 fkb=0 bkb=20\n"
    "wait 3\nclear_hitboxes\nwait_until 9\n"
    "hitbox slot=0 joint=@FOOT_L@ damage=10 size=2.40 x=0.00 y=0.00 z=0.00 angle=361 kbg=90 fkb=0 bkb=15\n"
    "wait 6\nclear_hitboxes\nwait_until 36\niasa\n";

inline const char *kFidelity = R"JSON({
 "schema": "synthetic-fidelity/1",
 "rows": [
  {"row": "Jab1", "motion": 44, "status": "SOURCE-RETIMED", "clip": "SYN_ATC_002", "source": "x", "source_clip": "x", "how": "", "deviation": "", "checked": []},
  {"row": "AirDown", "motion": 70, "status": "SOURCE-RETIMED", "clip": "SYN_ATC_007", "source": "x", "source_clip": "x", "how": "", "deviation": "", "checked": []}
 ]
}
)JSON";

inline const char *kPlan = R"JSON({
  "joints": [
    {"index": 0, "name": "TopN", "parent": null},
    {"index": 1, "name": "root", "parent": 0},
    {"index": 2, "name": "hand_r", "parent": 1},
    {"index": 3, "name": "foot_l", "parent": 1}
  ],
  "roles": {"hand.R": [2], "foot.L": [3]},
  "bank": {"clips": {"SYN_ATC_002": {"frames": 30}, "SYN_ATC_007": {"frames": 40}, "SYN_ATC_009": {"frames": 24}}},
  "motion_rows": [{"motion": 44, "row": "Jab1", "clip": "SYN_ATC_002"}, {"motion": 70, "row": "AirDown", "clip": "SYN_ATC_007"}]
})JSON";

inline const char *kProject = R"JSON({
  "schema": "workbench/1",
  "id": "synth",
  "gameplay": "gameplay.json",
  "moves_dir": "moves",
  "fidelity": "fidelity.json",
  "plan": "package/files/plan.json",
  "mod_id": "synth",
  "rebuild": ["python", "-c", "print('rebuilt')"],
  "import_clip": ["python", "-c", "import sys,json; print(json.dumps({'clip': 'SYN_IMPORTED', 'frames': 20}))"]
})JSON";

// Creates the project in `dir` (must exist). Returns dir.
inline QString makeSynthFighter(const QString &dir) {
    put(dir, "gameplay.json", kGameplay);
    put(dir, "moves/jab1.genoasm", kJab);
    put(dir, "moves/dair.genoasm", kDair);
    put(dir, "fidelity.json", kFidelity);
    put(dir, "package/files/plan.json", kPlan);
    put(dir, "workbench.json", kProject);
    return dir;
}
}
