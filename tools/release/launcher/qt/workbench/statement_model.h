#pragma once
#include <QJsonArray>
#include <QJsonObject>
#include <QString>
#include <functional>
namespace wb {
// Source statements are indexed together in their original source order.
class StatementModel {
public:
    using BoneResolver = std::function<int(const QString &)>;
    static StatementModel parse(const QString &source, BoneResolver resolveBone = {});
    QJsonArray statements() const;
    QJsonArray hurtWindows() const;
    QString edit(int ordinal, const QJsonObject &fields, QString *err, int *newOrdinal = nullptr) const;
    QString add(const QString &kind, int frame, const QJsonObject &fields, int *ordinal, QString *err) const;
    QString remove(int ordinal, QString *err) const;
private:
    QString source_;
    BoneResolver resolveBone_;
};
}
