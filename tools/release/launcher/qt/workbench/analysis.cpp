#include "analysis.h"
#include "commands.h"
#include <QJsonDocument>
#include <QSet>
#include <QRegularExpression>
#include <QMap>
#include <cmath>
#include <exception>

namespace wb {
namespace {
const QStringList roles{"HAND_L", "HAND_R", "FOOT_L", "FOOT_R", "ARM_L", "ARM_R",
    "LEG_L", "LEG_R", "TOE_L", "TOE_R", "UPARM_L", "UPARM_R", "UPLEG_L", "UPLEG_R",
    "HEAD", "CHEST", "HIPS", "FLOOR", "NECK", "SPINE"};

QJsonObject call(EngineBackend &engine, const QString &fn, const QJsonObject &args) {
    QString error;
    auto result = engine.call(fn, args, &error);
    if (!error.isEmpty()) throw CommandError{error};
    if (result.contains("ok") && !result["ok"].toBool())
        throw CommandError{result["error"].toString(t("engine call failed", "engine call failed"))};
    return result;
}
FrameInfo pose(EngineBackend &engine, int motion, int frame, bool aerial) {
    // An aerial staged at floor level lands before its active frames, so the engine lifts it (wb.frame lift).
    // The engine numbers a move's frames from 1; asking for frame 0 is answered "frame 1" and reads as past the end.
    frame = qMax(1, frame);
    QJsonObject frameArgs{{"motion", motion}, {"frame", frame}};
    if (aerial) frameArgs.insert("lift", 40);
    auto result = call(engine, "frame", frameArgs);
    // Backends normally return FrameInfo from frame; an acknowledgement-only
    // backend must supply the snapshot through frame_info instead.
    if (!result["bones"].isArray()) result = call(engine, "frame_info", {});
    if (!result["bones"].isArray())
        throw CommandError{t("engine returned no bone samples", "engine returned no bone samples")};
    for (const auto &value : result["bones"].toArray()) {
        const auto bone = value.toObject();
        const auto pos = bone["pos"].toObject();
        if (!bone["joint"].isDouble())
            throw CommandError{t("invalid engine bone sample", "invalid engine bone sample")};
        for (const char *axis : {"x", "y", "z"}) {
            if (!pos[axis].isDouble() || !std::isfinite(pos[axis].toDouble()))
                throw CommandError{t("invalid engine bone position", "invalid engine bone position")};
        }
    }
    return FrameInfo::fromJson(result);
}
struct SampleFrames { FrameInfo before, current; };
SampleFrames sampleFramesAt(EngineBackend &engine, int motion, const RowInfo &row, int frame) {
    auto before = pose(engine, motion, qMax(0, frame - 1), row.aerial);
    auto current = frame == 0 ? before : pose(engine, motion, frame, row.aerial);
    return {before, current};
}
// A hitbox may start after the engine's playable end of the move (a jab that chains into the next
// one, a clip longer than the action). Sample the last frame the engine can play instead of failing.
int lastPlayableFrame(const QString &message, int requested) {
    if (!message.contains("past the end of this move")) return -1;
    static const QRegularExpression lastRe("last frame (\\d+)"), atRe("fighter is at frame (\\d+)");
    auto m = lastRe.match(message);
    if (!m.hasMatch()) m = atRe.match(message);
    if (!m.hasMatch()) return -1;
    const int n = m.captured(1).toInt();
    return n >= 1 && n < requested ? n : -1;
}
SampleFrames sampleFrames(EngineBackend &engine, const RowInfo &row, int frame) {
    if (frame < 0) throw CommandError{t("frame must be nonnegative", "frame must be nonnegative")};
    const int motion = rowMotion(row);
    call(engine, "row", {{"motion", motion}});
    try {
        return sampleFramesAt(engine, motion, row, frame);
    } catch (const CommandError &error) {
        const int last = lastPlayableFrame(error.message, frame);
        if (last < 0) throw;
        call(engine, "row", {{"motion", motion}});
        return sampleFramesAt(engine, motion, row, last);
    }
}
const BoneLive *boneAt(const FrameInfo &frame, int joint) {
    for (const auto &bone : frame.bones) if (bone.joint == joint) return &bone;
    return nullptr;
}
double distance(const Vec3 &a, const Vec3 &b) {
    return std::hypot(a.x - b.x, a.y - b.y, a.z - b.z);
}
QVector<BoneSample> bonesAt(GenoData &data, const SampleFrames &frames) {
    const int torsoJoint = data.jointForRole("CHEST");
    const auto *torso = boneAt(frames.current, torsoJoint);
    if (torsoJoint < 0 || !torso)
        throw CommandError{t("CHEST role has no live bone sample", "CHEST role has no live bone sample")};
    QVector<BoneSample> bones;
    for (const auto &role : roles) {
        const int joint = data.jointForRole(role);
        if (joint < 0) continue;
        const auto *current = boneAt(frames.current, joint);
        const auto *before = boneAt(frames.before, joint);
        // Missing limbs are unknown; never invent a stationary sample.
        if (!current || !before) continue;
        bones.append({role, distance(current->pos, torso->pos), distance(current->pos, before->pos)});
    }
    return bones;
}
bool groundedClip(Session &s, const QString &clip) {
    // Reading diagnostics must not acknowledge a hand edit in the session store.
    FileStore reader(s.files().root());
    if (!reader.exists("ground_modes.json")) return false;
    QJsonParseError error;
    auto doc = QJsonDocument::fromJson(reader.read("ground_modes.json"), &error);
    if (error.error != QJsonParseError::NoError || !doc.isObject())
        throw CommandError{t("ground_modes.json is not a JSON object", "ground_modes.json is not a JSON object")};
    const auto grounded = doc.object()["grounded_clips"];
    if (grounded.isUndefined()) return false;
    if (!grounded.isArray())
        throw CommandError{t("grounded_clips must be an array", "grounded_clips must be an array")};
    for (const auto &name : grounded.toArray()) {
        if (!name.isString())
            throw CommandError{t("grounded_clips must contain strings", "grounded_clips must contain strings")};
        if (name.toString() == clip) return true;
    }
    return false;
}
} // namespace

RowAnalysis analyzeStaticRow(Session &s, const RowInfo &row, QString *err) {
    if (err) err->clear();
    try {
        RowAnalysis result;
        result.row = row.name; result.tag = row.tag; result.clip = row.clip;
        result.aerial = row.aerial; result.groundedClip = groundedClip(s, row.clip);
        static const QSet<QString> swingTags{"jab", "tilt", "smash", "aerial", "special"};
        result.hasSwingMotion = swingTags.contains(row.tag);
        result.timingIssues = s.data().timingProblems(row.name);
        for (const auto &hitbox : s.data().hitboxes(row.name))
            result.hitboxes.append({hitbox.ordinal, hitbox.joint, hitbox.startFrame, 0});
        return result;
    } catch (const CommandError &error) {
        if (err) *err = error.message;
    } catch (const std::exception &error) {
        if (err) *err = QString::fromUtf8(error.what());
    }
    return {};
}

QVector<BoneSample> sampleBones(EngineBackend &engine, GenoData &data, const RowInfo &row,
                                int frame, QString *err) {
    if (err) err->clear();
    try {
        return bonesAt(data, sampleFrames(engine, row, frame));
    } catch (const CommandError &error) {
        if (err) *err = error.message;
    } catch (const std::exception &error) {
        if (err) *err = QString::fromUtf8(error.what());
    }
    return {};
}

RowAnalysis analyzeRow(Session &s, const RowInfo &row, QString *err) {
    if (err) err->clear();
    try {
        QString error;
        auto result = analyzeStaticRow(s, row, &error);
        if (!error.isEmpty()) throw CommandError{error};
        if (!s.engine()) return result;
        // Sampling selects another engine row/frame, even if a later call fails.
        // Require an explicit load_row before further source-row playback.
        s.currentRow.clear();
        QMap<int, SampleFrames> frames;
        bool haveFloor = false;
        auto sample = [&](int frame) -> const SampleFrames & {
            if (!frames.contains(frame)) frames.insert(frame, sampleFrames(*s.engine(), row, frame));
            const auto &pair = frames[frame];
            const double lowest = qMin(pair.before.lowestY, pair.current.lowestY);
            if (!haveFloor) {
                result.floorY = pair.current.floorY; result.rowLowestY = lowest; haveFloor = true;
            } else result.rowLowestY = qMin(result.rowLowestY, lowest);
            return pair;
        };
        for (auto &hitbox : result.hitboxes) {
            const auto &pair = sample(hitbox.startFrame);
            auto bones = bonesAt(s.data(), pair);
            result.bonesByHitbox.insert(hitbox.ordinal, bones);
            result.bones.append(bones);
            hitbox.lowestY = pair.current.lowestY;
        }
        if (result.hitboxes.isEmpty()) {
            const auto &pair = sample(0);
            result.bones = bonesAt(s.data(), pair);
        }
        return result;
    } catch (const CommandError &error) {
        if (err) *err = error.message;
    } catch (const std::exception &error) {
        if (err) *err = QString::fromUtf8(error.what());
    }
    return {};
}
} // namespace wb
