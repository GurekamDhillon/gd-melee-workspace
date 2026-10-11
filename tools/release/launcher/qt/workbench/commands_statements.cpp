#include "commands.h"
namespace wb {
namespace {
QJsonObject fieldsArg(const QJsonObject &args,bool optional=false) {
    if(optional && !args.contains("fields"))return {};
    if(!args["fields"].isObject())throw CommandError{t("fields: expected an object","fields: se esperaba un objeto")};
    return args["fields"].toObject();
}
}
void registerStatementCommands(Session &s) {
    s.registry().add({"list_statements",t("List throw and hurt-state statements","Listar comandos de lanzamiento y vulnerabilidad"),
        commandSchema({{"row",argType("string")}}, {"row"}),false,
        [](const QJsonObject &args,CommandContext &ctx) {
            const auto row=args["row"].toString();needRow(ctx.session,row);
            return QJsonObject{{"statements",ctx.session.data().statements(row)},{"hurt_windows",ctx.session.data().hurtWindows(row)}};
        }});
    s.registry().add({"edit_statement",t("Edit a throw or hurt-state statement","Editar un comando de lanzamiento o vulnerabilidad"),
        commandSchema({{"row",argType("string")},{"ordinal",argType("integer")},{"fields",argType("object")},
                       {"frame",argType("integer")},{"propose",argType("boolean")}}, {"row","ordinal"}),true,
        [](const QJsonObject &args,CommandContext &ctx) {
            const auto row=args["row"].toString();needRow(ctx.session,row);
            const int ordinal=intArg(args,"ordinal");auto fields=fieldsArg(args,true);
            if(args.contains("frame")) {
                if(fields.contains("frame"))throw CommandError{t("Supply frame once","Indica el fotograma una sola vez")};
                fields["frame"]=intArg(args,"frame");
            }
            ctx.propose|=args["propose"].toBool();QString error;int newOrdinal=-1;
            const auto edits=ctx.session.data().editStatement(row,ordinal,fields,&newOrdinal,&error);
            if(!error.isEmpty())throw CommandError{error};
            auto result=ctx.session.commit(ctx,"edit_statement",args,t("Edit statement #%1 in %2","Editar comando #%1 en %2").arg(ordinal).arg(row),edits);
            result["ordinal"]=newOrdinal;return result;
        }});
    s.registry().add({"add_statement",t("Add a throw or hurt-state statement","Añadir un comando de lanzamiento o vulnerabilidad"),
        commandSchema({{"row",argType("string")},{"kind",argType("string")},{"frame",argType("integer")},
                       {"fields",argType("object")},{"propose",argType("boolean")}}, {"row","kind","frame"}),true,
        [](const QJsonObject &args,CommandContext &ctx) {
            const auto row=args["row"].toString();needRow(ctx.session,row);
            const int frame=intArg(args,"frame");const auto fields=fieldsArg(args,true);
            ctx.propose|=args["propose"].toBool();QString error;int ordinal=-1;
            const auto edits=ctx.session.data().addStatement(row,args["kind"].toString(),frame,fields,&ordinal,&error);
            if(!error.isEmpty())throw CommandError{error};
            auto result=ctx.session.commit(ctx,"add_statement",args,t("Add statement in %1 at frame %2","Añadir comando en %1 en el fotograma %2").arg(row).arg(frame),edits);
            result["ordinal"]=ordinal;return result;
        }});
    s.registry().add({"delete_statement",t("Delete a throw or hurt-state statement","Eliminar un comando de lanzamiento o vulnerabilidad"),
        commandSchema({{"row",argType("string")},{"ordinal",argType("integer")},{"propose",argType("boolean")}}, {"row","ordinal"}),true,
        [](const QJsonObject &args,CommandContext &ctx) {
            const auto row=args["row"].toString();needRow(ctx.session,row);const int ordinal=intArg(args,"ordinal");
            ctx.propose|=args["propose"].toBool();QString error;
            const auto edits=ctx.session.data().removeStatement(row,ordinal,&error);
            if(!error.isEmpty())throw CommandError{error};
            auto result=ctx.session.commit(ctx,"delete_statement",args,t("Delete statement #%1 in %2","Eliminar comando #%1 en %2").arg(ordinal).arg(row),edits);
            result["ordinal"]=ordinal;return result;
        }});
}
}
