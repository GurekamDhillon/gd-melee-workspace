#pragma once
#include "checks.h"
#include "geno_data.h"
#include "history.h"
#include <QJsonArray>
#include <QJsonObject>
#include <QListWidget>
#include <QMap>
#include <QTableWidget>
#include <QTreeWidget>
#include <QVariant>
#include <QWidget>

class QAction;
class QLabel;

namespace wb {
class Session;

class OutlinerPanel : public QTreeWidget {
    Q_OBJECT
public:
    explicit OutlinerPanel(QWidget *parent = nullptr);
    // Standalone, same-thread sessions only. The window supplies worker snapshots.
    void setSession(Session &session);
    void refresh();
    void setRows(const QVector<RowInfo> &, const QMap<QString, QVector<HitboxRef>> &);
    void setSelection(const QString &row, int ordinal = -1); // Feedback, no signals.
signals:
    void rowSelected(const QString &row);
    void hitboxSelected(const QString &row, int ordinal);
private:
    Session *session_ = nullptr;
};

class InspectorPanel : public QWidget {
    Q_OBJECT
public:
    explicit InspectorPanel(QWidget *parent = nullptr);
    void showHitbox(const QString &row, const HitboxRef &hitbox);
    void clear();
public slots:
    void setField(const QString &field, const QVariant &value);
signals:
    void editRequested(const QString &command, const QJsonObject &args);
private:
    void updateEditors(const QJsonObject &previous = {});
    QString row_;
    int ordinal_ = -1;
    QJsonObject values_;
    QMap<QString, QWidget *> editors_;
    QLabel *title_;
};

class ProblemsPanel : public QListWidget {
    Q_OBJECT
public:
    explicit ProblemsPanel(QWidget *parent = nullptr);
    void setProblems(const QVector<Problem> &);
signals:
    void problemActivated(const QString &row, int ordinal);
};

class ClipBrowserPanel : public QListWidget {
    Q_OBJECT
public:
    explicit ClipBrowserPanel(QWidget *parent = nullptr);
    void setClips(const QVector<ClipInfo> &, const QString &current);
public slots:
    void previewCurrent();
    void assignCurrent();
signals:
    void previewRequested(const QString &clip);
    void assignRequested(const QString &clip);
private:
    QString current_;
    QAction *preview_, *assign_;
};

class FidelityPanel : public QTableWidget {
    Q_OBJECT
public:
    explicit FidelityPanel(QWidget *parent = nullptr);
    void setFidelity(const QJsonArray &entries, const QString &row, const QVector<int> &motions = {});
};

class ReviewPanel : public QTableWidget {
    Q_OBJECT
public:
    explicit ReviewPanel(QWidget *parent = nullptr);
    void setHistory(const QVector<HistoryEntry> &);
    bool actionsEnabled(int row) const;
public slots:
    void accept(int row);
    void reject(int row);
signals:
    void acceptRequested(int id);
    void rejectRequested(int id);
    void undoRequested();
    void redoRequested();
private:
    void requestProposal(int id, bool accepting);
    QVector<HistoryEntry> entries_;
};
} // namespace wb
