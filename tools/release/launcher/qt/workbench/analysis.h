#pragma once
#include "checks.h"
#include "engine_link.h"
#include "geno_data.h"

namespace wb {
class Session;
RowAnalysis analyzeStaticRow(Session &, const RowInfo &, QString *err);
RowAnalysis analyzeRow(Session &, const RowInfo &, QString *err);
QVector<BoneSample> sampleBones(EngineBackend &, GenoData &, const RowInfo &, int frame, QString *err);
} // namespace wb
