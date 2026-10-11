#include "statement_model.h"
#include <QMap>
#include <QRegularExpression>
#include <QSet>
#include <QStringList>
#include <algorithm>
#include <cmath>
#include <limits>
#include <utility>

namespace wb {
namespace {
struct Token { QString text; qsizetype at; };
QVector<Token> tokens(const QString &line) {
    static const QRegularExpression re("\\S+");
    const auto comment=line.indexOf('#');
    auto it=re.globalMatch(comment<0 ? line : line.left(comment));
    QVector<Token> out;
    while(it.hasNext()) { const auto m=it.next(); out.append({m.captured(),m.capturedStart()}); }
    return out;
}
bool number(const QString &text, quint32 *out) {
    bool ok=false;
    const auto n=text.toULongLong(&ok,text.startsWith("0x",Qt::CaseInsensitive)?16:10);
    if(!ok || n>0xFFFFFFFFull || text.startsWith('-')) return false;
    *out=quint32(n); return true;
}
bool wordNumber(const QString &text, quint32 *out) {
    if(!text.startsWith('-'))return number(text,out);
    bool ok=false;const qint64 value=text.toLongLong(&ok,0);
    if(!ok || value<std::numeric_limits<qint32>::min() || value>=0)return false;
    *out=quint32(value);return true;
}
int stateNumber(const QString &text) {
    const auto s=text.toLower();
    if(s=="normal") return 0;
    if(s=="invincible") return 1;
    if(s=="intangible") return 2;
    quint32 n; return number(text,&n) && n<=std::numeric_limits<int>::max() ? int(n) : -1;
}
bool boneValid(const QString &s) {
    static const QRegularExpression role("^@[A-Za-z_][A-Za-z0-9_]*@$" );
    quint32 n; return role.match(s).hasMatch() || (number(s,&n) && n<=255);
}
QString kindOf(const QString &op) {
    if(op=="throw" || op=="throw_hitbox") return "throw";
    if(op=="throw_release" || op=="throw_flag") return "throw_release";
    if(op=="body_state" || op=="hurtboxes_state" || op=="hurtbox_state") return op;
    return {};
}
QStringList fieldNames(const QString &kind) {
    if(kind=="throw") return {"slot","damage","angle","kbg","fkb","bkb","element","sfx_severity","sfx_kind"};
    if(kind=="throw_release" || kind=="throw_flag") return {"flag"};
    if(kind=="hurtbox_state") return {"bone","state"};
    return {"state"};
}
QString canonicalKey(const QString &kind,const QString &key) {
    if(kind=="throw") {
        static const QMap<QString,QString> aliases{
            {"idx","slot"},{"w0.idx","slot"},{"w0.damage","damage"},
            {"unk0","angle"},{"w1.unk0","angle"},{"hit_x24","kbg"},{"w1.hit_x24","kbg"},
            {"hit_x28","fkb"},{"w1.hit_x28","fkb"},{"hit_x2C","bkb"},{"w2.hit_x2C","bkb"},
            {"w2.element","element"},{"w2.sfx_severity","sfx_severity"},{"w2.sfx_kind","sfx_kind"}};
        return aliases.contains(key)?aliases[key]:(fieldNames(kind).contains(key)?key:QString());
    }
    if(kind=="throw_release" && (key=="hit_idx" || key=="w0.hit_idx")) return "flag";
    if(kind=="hurtbox_state" && (key=="bone_idx" || key=="w0.bone_idx")) return "bone";
    if(key=="w0.state" && kind.endsWith("state")) return "state";
    return fieldNames(kind).contains(key) && key!="flag" ? key : QString();
}
int maximum(const QString &key) {
    if(key=="damage") return 8388607;
    if(key=="slot") return 1;
    if(key=="state") return 2;
    if(key=="element" || key=="sfx_kind") return 15;
    if(key=="sfx_severity") return 7;
    return 511;
}
struct Ref {
    int ordinal=0,line=0,frame=-1;
    QString kind,note,noteEs,noteCode;
    QJsonObject fields;
    QMap<QString,int> tokenFor;
    QVector<quint32> payload;
    bool editable=true,raw=false,decoded=false;
};
// Notes travel with both language variants; the offline command library has no UI language state.
void readOnly(Ref &r,const QString &why) {
    static const QMap<QString,QPair<QString,QString>> messages{
        {"Malformed throw payload",{"malformed_payload","Datos de lanzamiento mal formados"}},
        {"Malformed statement payload",{"malformed_payload","Datos del comando mal formados"}},
        {"Reserved throw bits: edit the original source by hand",{"raw","Bits de lanzamiento reservados: edita el código original a mano"}},
        {"Raw command: original bits are preserved",{"raw","Comando sin decodificar: se conservan los bits originales"}},
        {"Malformed positional statement",{"malformed_payload","Comando posicional mal formado"}},
        {"throw_release must be bare",{"release_arguments","throw_release no admite argumentos"}},
        {"Unknown or repeated field: edit the source by hand",{"unknown_field","Campo desconocido o repetido: edita el código a mano"}},
        {"Bone must be a joint index or @ROLE@",{"invalid_bone","El hueso debe ser un índice de articulación o @ROLE@"}},
        {"Malformed numeric field",{"invalid_statement","Campo numérico mal formado"}},
        {"Nonzero throw flag sets another engine flag; it is not a release",{"raw","Una bandera de lanzamiento distinta de cero activa otra bandera del motor; no libera al rival"}},
        {"Engine throw slots are 0 and 1; this source slot is unsafe",{"slot_range","Los índices de lanzamiento del motor son 0 y 1; este índice no es seguro"}},
        {"Unknown hurt state: original value is preserved",{"unknown_state","Estado de vulnerabilidad desconocido: se conserva el valor original"}},
        {"Throw field outside engine range",{"throw_range","Campo de lanzamiento fuera del rango del motor"}}};
    r.editable=false;
    if(r.note.isEmpty()) {r.note=why;const auto message=messages.value(why,{"invalid_statement","Comando no compatible"});r.noteCode=message.first;r.noteEs=message.second;}
}
void decode(Ref &r,const QVector<quint32> &p) {
    if(r.kind=="throw") {
        if(p.size()!=3 || p[0]>0x3FFFFFFu) { readOnly(r,"Malformed throw payload"); return; }
        r.fields={{"slot",int(p[0]>>23)},{"damage",int(p[0]&0x7FFFFF)},
                  {"angle",int(p[1]>>23)},{"kbg",int((p[1]>>14)&511)},{"fkb",int((p[1]>>5)&511)},
                  {"bkb",int(p[2]>>23)},{"element",int((p[2]>>19)&15)},
                  {"sfx_severity",int((p[2]>>16)&7)},{"sfx_kind",int((p[2]>>12)&15)}};
        if((p[1]&31) || (p[2]&4095)) readOnly(r,"Reserved throw bits: edit the original source by hand");
    } else {
        if(p.size()!=1 || p[0]>0x3FFFFFFu) { readOnly(r,"Malformed statement payload"); return; }
        if(r.kind=="throw_release") r.fields={{"flag",int(p[0])}};
        else if(r.kind=="hurtbox_state") r.fields={{"bone",QString::number(p[0]>>18)},{"state",int(p[0]&0x3FFFF)}};
        else r.fields={{"state",int(p[0])}};
    }
    r.decoded=true;
}
Ref readRef(const QVector<Token> &w,int line,int frame,int ordinal) {
    Ref r; r.line=line; r.frame=frame; r.ordinal=ordinal; r.kind=kindOf(w[0].text.toLower());
    for(const auto &key:fieldNames(r.kind)) r.fields[key]=key=="bone"?QJsonValue("0"):QJsonValue(0);
    if(w.size()>1 && w[1].text.startsWith("raw=")) {
        r.raw=true;
        const auto parts=w[1].text.mid(4).split(','); QVector<quint32> p;
        for(const auto &s:parts) { quint32 n; if(!wordNumber(s,&n)) {p.clear();break;} p.append(n); }
        if(!p.isEmpty()) {
            const int want=r.kind=="throw"?34:r.kind=="throw_release"?20:r.kind=="body_state"?26:r.kind=="hurtboxes_state"?27:28;
            if(int(p[0]>>26)==want) {p[0]&=0x3FFFFFFu;decode(r,p);}
        }
        if(w.size()!=2)r.decoded=false;
        readOnly(r,"Raw command: original bits are preserved");
    } else if(w.size()>1 && !w[1].text.contains('=')) {
        for(int i=1;i<w.size();++i) {quint32 n;if(!(i==1?number(w[i].text,&n):wordNumber(w[i].text,&n))){readOnly(r,"Malformed positional statement");break;}r.payload.append(n);}
        decode(r,r.payload);
        if(w[0].text.toLower()=="throw_release") readOnly(r,"throw_release must be bare");
    } else {
        for(int i=1;i<w.size();++i) {
            const int eq=int(w[i].text.indexOf('='));
            const auto key=canonicalKey(r.kind,w[i].text.left(eq));
            if(eq<1 || key.isEmpty() || r.tokenFor.contains(key)) {readOnly(r,"Unknown or repeated field: edit the source by hand");continue;}
            r.tokenFor[key]=i; const auto value=w[i].text.mid(eq+1);
            if(key=="bone") {
                if(!boneValid(value)) readOnly(r,"Bone must be a joint index or @ROLE@");
                quint32 n; r.fields[key]=number(value,&n)?QString::number(n):value;
            } else {
                const int state=key=="state"?stateNumber(value):-1; quint32 n=0;
                if(key=="state" && state>=0) n=quint32(state);
                else if(!number(value,&n) || n>quint32(std::numeric_limits<int>::max())) {readOnly(r,"Malformed numeric field");continue;}
                r.fields[key]=int(n);
            }
        }
        if(w[0].text.toLower()=="throw_release" && w.size()!=1) readOnly(r,"throw_release must be bare");
    }
    if(r.kind=="throw_release") {
        if(r.fields["flag"].toInt()!=0) {r.kind="throw_flag";readOnly(r,"Nonzero throw flag sets another engine flag; it is not a release");}
        else r.fields={};
    }
    if(r.kind=="throw" && r.fields["slot"].toInt()>1) readOnly(r,"Engine throw slots are 0 and 1; this source slot is unsafe");
    if(r.fields.contains("state") && (r.fields["state"].toInt()<0 || r.fields["state"].toInt()>2)) readOnly(r,"Unknown hurt state: original value is preserved");
    if(r.kind=="throw") for(auto it=r.fields.begin();it!=r.fields.end();++it)
        if(it.value().toInt()<0 || it.value().toInt()>maximum(it.key())) readOnly(r,"Throw field outside engine range");
    return r;
}
bool waitOp(const QVector<Token> &w) { return !w.isEmpty() && QSet<QString>{"wait","wait_until","frame"}.contains(w[0].text.toLower()); }
bool terminal(const QVector<Token> &w) {return !w.isEmpty() && w[0].text.compare("end",Qt::CaseInsensitive)==0;}
bool flow(const QVector<Token> &w) {
    if(w.isEmpty()) return false;
    const auto op=w[0].text.toLower();
    if(op=="call") return w.size()<2 || w[1].text.compare("geno.article.spawn",Qt::CaseInsensitive)!=0;
    static const QSet<QString> names{"loop","loop_end","endloop","subroutine","return","goto","if","ifv","branch","skip","orig","chg","chgand","chgclr","wait_anim","continuation"};
    return names.contains(op);
}
bool advance(const QVector<Token> &w,int *time) {
    quint32 n=0;
    if(w.size()!=2 || !number(w[1].text,&n) || n>0x3FFFFFFu) return false;
    const qint64 next=w[0].text.compare("wait",Qt::CaseInsensitive)==0?qint64(*time)+n:std::max<qint64>(*time,n);
    if(next>std::numeric_limits<int>::max()) return false;
    *time=int(next); return true;
}
struct Scan { QVector<Ref> refs; QVector<int> frames; bool timingSafe=true; int barrier=-1; };
Scan scan(const QStringList &lines) {
    Scan s; int time=0; bool known=true,ended=false;
    for(int i=0;i<lines.size();++i) {
        const auto w=tokens(lines[i]); s.frames.append(known && !ended?time:-1);
        if(w.isEmpty()) continue;
        if(!kindOf(w[0].text.toLower()).isEmpty()) s.refs.append(readRef(w,i,known && !ended?time:-1,int(s.refs.size())));
        if(ended) continue;
        if(terminal(w)) {ended=true;if(s.barrier<0)s.barrier=i;continue;}
        if(flow(w) || (waitOp(w) && (!known || !advance(w,&time)))) {
            known=false;s.timingSafe=false;if(s.barrier<0)s.barrier=i;
        }
    }
    if(!s.timingSafe) for(auto &r:s.refs) {
        if(!r.note.isEmpty())r.note+="; ";if(!r.noteEs.isEmpty())r.noteEs+="; ";
        r.note+="Timing unsupported beyond control flow or an opaque timer";
        r.noteEs+="No se puede calcular el tiempo tras un salto, bucle o temporizador opaco";
    }
    return s;
}
QJsonArray windows(const Scan &s,const StatementModel::BoneResolver &resolveBone) {
    QJsonArray out; QMap<QString,int> active;
    for(const auto &r:s.refs) {
        if(r.frame<0 || (s.barrier>=0 && r.line>=s.barrier)) break;
        if(!r.kind.endsWith("state")) continue;
        // Invalid syntax and unknown states do not prove that an earlier state was reset.
        if((!r.editable && (!r.raw || !r.decoded)) || r.fields["state"].toInt(-1)<0 || r.fields["state"].toInt()>2)break;
        const auto bone=r.fields["bone"].toString();
        const int joint=resolveBone && bone.startsWith('@')?resolveBone(bone):-1;
        const auto identity=joint>=0?QString::number(joint):bone;
        const auto key=r.kind=="body_state"?QString("body"):r.kind=="hurtboxes_state"?QString("capsules"):"bone:"+identity;
        QStringList close{key};
        if(r.kind=="hurtboxes_state") for(auto it=active.begin();it!=active.end();++it) if(it.key().startsWith("bone:"))close.append(it.key());
        for(const auto &k:close) if(active.contains(k)) {const int idx=active.take(k);auto o=out[idx].toObject();o["end_frame"]=r.frame;out[idx]=o;}
        const int state=r.fields["state"].toInt(-1);
        if(state<1 || state>2) continue;
        active[key]=int(out.size());
        out.append(QJsonObject{{"ordinal",r.ordinal},{"kind",r.kind},{"bone",bone},{"bone_identity",identity},
                               {"state",state},{"start_frame",r.frame},{"end_frame",-1}});
    }
    return out;
}
QVector<quint32> encode(const Ref &r,const QJsonObject &f) {
    if(r.kind=="throw") return {
        quint32(f["slot"].toInt())<<23 | quint32(f["damage"].toInt()),
        quint32(f["angle"].toInt())<<23 | quint32(f["kbg"].toInt())<<14 | quint32(f["fkb"].toInt())<<5,
        quint32(f["bkb"].toInt())<<23 | quint32(f["element"].toInt())<<19 | quint32(f["sfx_severity"].toInt())<<16 | quint32(f["sfx_kind"].toInt())<<12};
    if(r.kind=="hurtbox_state") return {quint32(f["bone"].toString().toUInt())<<18 | quint32(f["state"].toInt())};
    return {quint32(f["state"].toInt())};
}
bool mergedFields(const Ref &r,const QJsonObject &changes,QJsonObject *out,QString *err) {
    *out=r.fields;
    for(auto it=changes.begin();it!=changes.end();++it) {
        const auto key=it.key(); if(key=="frame") continue;
        if(!r.fields.contains(key)) {*err="Unknown field: "+key;return false;}
        if(key=="bone") {
            QString b;
            if(it.value().isString()) b=it.value().toString();
            else if(it.value().isDouble() && std::floor(it.value().toDouble())==it.value().toDouble()) b=QString::number(it.value().toDouble(),'f',0);
            if(!boneValid(b)) {*err="Bone must be a joint index or @ROLE@";return false;}
            quint32 n; (*out)[key]=number(b,&n)?QString::number(n):b;
        } else {
            const double n=it.value().toDouble(-1);
            if(!it.value().isDouble() || !std::isfinite(n) || std::floor(n)!=n || n<0 || n>maximum(key)) {*err="Integer outside engine range: "+key;return false;}
            (*out)[key]=int(n);
        }
    }
    return true;
}
QString patchedLine(const QString &line,const Ref &r,const QJsonObject &f) {
    QString out=line; const auto w=tokens(line);
    if(!r.payload.isEmpty()) {
        if(r.kind=="hurtbox_state" && f["bone"].toString().startsWith('@')) {
            const auto end=w.last().at+w.last().text.size();
            out.replace(w[0].at,end-w[0].at,"hurtbox_state bone="+f["bone"].toString()+" state="+QString::number(f["state"].toInt()));
            return out;
        }
        const auto p=encode(r,f);
        for(int i=int(p.size())-1;i>=0;--i) if(p[i]!=r.payload[i]) out.replace(w[i+1].at,w[i+1].text.size(),QString::number(p[i]));
        return out;
    }
    struct Patch {qsizetype at,length;QString text;}; QVector<Patch> patches;QString append;
    for(auto it=f.begin();it!=f.end();++it) {
        if(it.value()==r.fields[it.key()]) continue;
        const auto value=it.value().isString()?it.value().toString():QString::number(it.value().toInt());
        if(r.tokenFor.contains(it.key())) {
            const auto &t=w[r.tokenFor[it.key()]];const auto eq=t.text.indexOf('=');
            patches.append({t.at+eq+1,t.text.size()-eq-1,value});
        } else append+=' '+it.key()+'='+value;
    }
    if(!append.isEmpty()) patches.append({w.last().at+w.last().text.size(),0,append});
    std::sort(patches.begin(),patches.end(),[](const Patch &a,const Patch &b){return a.at>b.at;});
    for(const auto &p:patches) out.replace(p.at,p.length,p.text);
    return out;
}
QString crOf(const QStringList &lines) {for(const auto &l:lines)if(l.endsWith('\r'))return "\r";return {};}
void setWait(QString &line,int value) {const auto w=tokens(line);line.replace(w[1].at,w[1].text.size(),QString::number(value));}
bool insertAt(QStringList &lines,int frame,const QString &newLine,int *at,QString *err) {
    int time=0;const auto cr=crOf(lines);
    for(int i=0;i<lines.size();++i) {
        const auto w=tokens(lines[i]);if(w.isEmpty())continue;
        if(terminal(w)) {
            if(frame>time){*err="Cannot place a statement after the script ends";return false;}
            lines.insert(i,newLine);*at=i;return true;
        }
        if(!waitOp(w)) continue;
        int next=time;if(!advance(w,&next)){*err="Opaque timer: edit timing by hand";return false;}
        if(frame==time){lines.insert(i,newLine);*at=i;return true;}
        if(frame>time && frame<next) {
            if(w[0].text.compare("wait",Qt::CaseInsensitive)==0) {
                setWait(lines[i],frame-time);lines.insert(i+1,newLine);
                lines.insert(i+2,QString("wait %1").arg(next-frame)+cr);*at=i+1;
            } else {lines.insert(i,QString("wait_until %1").arg(frame)+cr);lines.insert(i+1,newLine);*at=i+1;}
            return true;
        }
        time=next;
    }
    int pos=int(lines.size());if(pos && lines.last().isEmpty())--pos;
    if(frame>time){lines.insert(pos,QString("wait_until %1").arg(frame)+cr);++pos;}
    lines.insert(pos,newLine);*at=pos;return true;
}
QVector<QPair<QString,int>> commands(const QStringList &lines,int omit=-1) {
    QVector<QPair<QString,int>> out;const auto s=scan(lines);
    for(int i=0;i<lines.size();++i) {const auto w=tokens(lines[i]);if(i==omit || w.isEmpty() || waitOp(w))continue;
        QStringList code;for(const auto &t:w)code.append(t.text);out.append({code.join(' '),s.frames[i]});}
    return out;
}
QString failure(QString *err,const QString &why) {if(err)*err=why;return {};}
}

StatementModel StatementModel::parse(const QString &s,BoneResolver resolveBone) { StatementModel m; m.source_=s; m.resolveBone_=std::move(resolveBone);return m; }
QJsonArray StatementModel::statements() const {
    const auto s=scan(source_.split('\n'));const auto win=windows(s,resolveBone_);QJsonArray out;
    for(const auto &r:s.refs) {
        int end=-1;for(const auto &v:win)if(v.toObject()["ordinal"].toInt()==r.ordinal)end=v.toObject()["end_frame"].toInt(-1);
        out.append(QJsonObject{{"ordinal",r.ordinal},{"line",r.line},{"kind",r.kind},{"frame",r.frame},{"end_frame",end},
                               {"editable",r.editable},{"timing_editable",r.editable && s.timingSafe && r.frame>=0},
                               {"timing_uncertain",!s.timingSafe || r.frame<0},
                               {"note",r.note},{"note_es",r.noteEs},{"note_code",r.noteCode},{"fields",r.fields}});
    }
    return out;
}
QJsonArray StatementModel::hurtWindows() const {return windows(scan(source_.split('\n')),resolveBone_);}
QString StatementModel::edit(int ordinal,const QJsonObject &changes,QString *err,int *newOrdinal) const {
    if(err)err->clear();if(newOrdinal)*newOrdinal=-1;QString error;auto lines=source_.split('\n');const auto s=scan(lines);
    if(ordinal<0 || ordinal>=s.refs.size())return failure(err,"Unknown statement ordinal");
    const auto r=s.refs[ordinal];if(!r.editable)return failure(err,r.note);
    QJsonObject f;if(!mergedFields(r,changes,&f,&error))return failure(err,error);
    lines[r.line]=patchedLine(lines[r.line],r,f);
    if(!changes.contains("frame")){if(newOrdinal)*newOrdinal=ordinal;return lines.join('\n');}
    const double value=changes["frame"].toDouble(-1);
    if(!changes["frame"].isDouble() || !std::isfinite(value) || std::floor(value)!=value || value<0 || value>0x3FFFFFF)return failure(err,"Frame must be an integer in the engine timer range");
    if(!s.timingSafe || r.frame<0)return failure(err,"Timing unsupported: control flow or opaque timer");
    const int frame=int(value);if(frame==r.frame){if(newOrdinal)*newOrdinal=ordinal;return lines.join('\n');}
    const auto keep=commands(lines,r.line);const auto moved=lines.takeAt(r.line);int at=-1;
    if(!insertAt(lines,frame,moved,&at,&error))return failure(err,error);
    if(commands(lines,at)!=keep || scan(lines).frames[at]!=frame)return failure(err,"Could not move statement without moving other commands");
    if(newOrdinal)for(const auto &ref:scan(lines).refs)if(ref.line==at)*newOrdinal=ref.ordinal;
    return lines.join('\n');
}
QString StatementModel::add(const QString &kind,int frame,const QJsonObject &fields,int *ordinal,QString *err) const {
    if(err)err->clear();if(ordinal)*ordinal=-1;
    if(kindOf(kind)!=kind || kind=="throw_flag")return failure(err,"Unsupported statement kind");
    if(frame<0 || frame>0x3FFFFFF)return failure(err,"Frame must be in the engine timer range");
    auto lines=source_.split('\n');const auto s=scan(lines);
    if(!s.timingSafe)return failure(err,"Timing unsupported: control flow or opaque timer");
    Ref r=readRef(tokens(kind),0,0,0);QJsonObject f;QString error;
    if(fields.contains("frame"))return failure(err,"Supply frame separately");
    if(!mergedFields(r,fields,&f,&error))return failure(err,error);
    QString line=kind;
    if(kind!="throw_release")for(const auto &key:fieldNames(kind))line+=' '+key+'='+(f[key].isString()?f[key].toString():QString::number(f[key].toInt()));
    line+=crOf(lines);const auto keep=commands(lines);int at=-1;
    if(!insertAt(lines,frame,line,&at,&error))return failure(err,error);
    const auto after=scan(lines);
    if(commands(lines,at)!=keep || after.frames[at]!=frame)return failure(err,"Could not add statement without moving other commands");
    for(const auto &ref:after.refs)if(ref.line==at && ordinal)*ordinal=ref.ordinal;
    return lines.join('\n');
}
QString StatementModel::remove(int ordinal,QString *err) const {
    if(err)err->clear();auto lines=source_.split('\n');const auto s=scan(lines);
    if(ordinal<0 || ordinal>=s.refs.size())return failure(err,"Unknown statement ordinal");
    if(!s.refs[ordinal].editable)return failure(err,s.refs[ordinal].note);
    lines.removeAt(s.refs[ordinal].line);return lines.isEmpty()?QStringLiteral(""):lines.join('\n');
}
}
