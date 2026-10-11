#include "geno_data.h"
#include "statement_model.h"
#include <stdexcept>
namespace wb {
namespace {
[[noreturn]] void fail(const QString &s) {throw std::runtime_error(s.toUtf8().constData());}
QString textOf(const QByteArray &bytes) {
    const auto body=bytes.startsWith("\xEF\xBB\xBF")?bytes.mid(3):bytes;
    const auto text=QString::fromUtf8(body);
    if(text.toUtf8()!=body)fail("Statement source is not valid UTF-8");
    return text;
}
QVector<FileChange> changes(const QString &path,const QByteArray &before,const QString &after) {
    if(after.isNull())fail("Could not edit statement source");
    const auto bytes=(before.startsWith("\xEF\xBB\xBF")?QByteArray("\xEF\xBB\xBF"):QByteArray())+after.toUtf8();
    return bytes==before?QVector<FileChange>{}:QVector<FileChange>{{path,before,bytes}};
}
}
QJsonArray GenoData::statements(const QString &name) const {
    const auto row=findRow(name);
    if(!row || row->script.isEmpty() || !scripts_.contains(row->script))return {};
    return StatementModel::parse(textOf(scripts_.value(row->script)),[this](const QString &bone){return jointForRole(bone);}).statements();
}
QJsonArray GenoData::hurtWindows(const QString &name) const {
    const auto row=findRow(name);
    if(!row || row->script.isEmpty() || !scripts_.contains(row->script))return {};
    return StatementModel::parse(textOf(scripts_.value(row->script)),[this](const QString &bone){return jointForRole(bone);}).hurtWindows();
}
QVector<FileChange> GenoData::editStatement(const QString &name,int ordinal,const QJsonObject &fields,QString *err) const {
    return editStatement(name,ordinal,fields,nullptr,err);
}
QVector<FileChange> GenoData::editStatement(const QString &name,int ordinal,const QJsonObject &fields,int *newOrdinal,QString *err) const {
    if(err)err->clear();
    if(newOrdinal)*newOrdinal=-1;
    try {
        const auto row=findRow(name);if(!row)fail("Unknown row: "+name);
        if(row->script.isEmpty() || !scripts_.contains(row->script))fail("Row has no script: "+name);
        const auto conflict=externalError({"workbench.json",project_.gameplay,row->script});if(!conflict.isEmpty())fail(conflict);
        const auto bytes=scripts_.value(row->script);QString error;
        const auto after=StatementModel::parse(textOf(bytes)).edit(ordinal,fields,&error,newOrdinal);
        if(!error.isEmpty())fail(error);
        return changes(row->script,bytes,after);
    } catch(const std::exception &e) {if(err)*err=QString::fromUtf8(e.what());return {};}
}
QVector<FileChange> GenoData::addStatement(const QString &name,const QString &kind,int frame,const QJsonObject &fields,int *ordinal,QString *err) const {
    if(err)err->clear();if(ordinal)*ordinal=-1;
    try {
        const auto row=findRow(name);if(!row)fail("Unknown row: "+name);
        if(row->script.isEmpty() || !scripts_.contains(row->script))fail("Row has no script: "+name);
        const auto conflict=externalError({"workbench.json",project_.gameplay,row->script});if(!conflict.isEmpty())fail(conflict);
        const auto bytes=scripts_.value(row->script);QString error;
        const auto after=StatementModel::parse(textOf(bytes)).add(kind,frame,fields,ordinal,&error);
        if(!error.isEmpty())fail(error);
        return changes(row->script,bytes,after);
    } catch(const std::exception &e) {if(err)*err=QString::fromUtf8(e.what());return {};}
}
QVector<FileChange> GenoData::removeStatement(const QString &name,int ordinal,QString *err) const {
    if(err)err->clear();
    try {
        const auto row=findRow(name);if(!row)fail("Unknown row: "+name);
        if(row->script.isEmpty() || !scripts_.contains(row->script))fail("Row has no script: "+name);
        const auto conflict=externalError({"workbench.json",project_.gameplay,row->script});if(!conflict.isEmpty())fail(conflict);
        const auto bytes=scripts_.value(row->script);QString error;
        const auto after=StatementModel::parse(textOf(bytes)).remove(ordinal,&error);
        if(!error.isEmpty())fail(error);
        return changes(row->script,bytes,after);
    } catch(const std::exception &e) {if(err)*err=QString::fromUtf8(e.what());return {};}
}
}
