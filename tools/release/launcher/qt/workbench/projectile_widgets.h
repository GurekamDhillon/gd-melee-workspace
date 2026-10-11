#pragma once
// Projectiles in the Workbench: a lane of spawn markers under the move timeline, and the Projectiles inspector tab.
// Both only emit command requests (edit_spawn, add_spawn, delete_spawn, edit_article, add_article, ...): the window
// runs them through the session like every other edit. New widgets; the timeline's own code is untouched.
#include <QJsonArray>
#include <QJsonObject>
#include <QMap>
#include <QWidget>

class QComboBox;
class QDoubleSpinBox;
class QLabel;
class QListWidget;
class QPushButton;
class QSpinBox;
class QTableWidget;
class QVBoxLayout;

namespace wb {
class TimelineView;

class SpawnLane : public QWidget {
    Q_OBJECT
public:
    explicit SpawnLane(QWidget *parent = nullptr);
    void setTimeline(TimelineView *timeline);
    // The spawns of one row (list_spawns records) and the article names, by index.
    void setSpawns(const QString &row, const QJsonArray &spawns, const QStringList &articleNames);
    int spawnCount() const { return spawns_.size(); }
    QRectF chipRect(int ordinal) const;   // lane coordinates; empty when unknown
    int frameAt(qreal x) const;           // the move frame under lane x, clamped to the timeline's range
    QSize sizeHint() const override { return {200, 30}; }
    QSize minimumSizeHint() const override { return {80, 30}; }
signals:
    void editRequested(const QString &command, const QJsonObject &args);
    void spawnSelected(int ordinal);
protected:
    void paintEvent(QPaintEvent *) override;
    void mousePressEvent(QMouseEvent *) override;
    void mouseMoveEvent(QMouseEvent *) override;
    void mouseReleaseEvent(QMouseEvent *) override;
    void keyPressEvent(QKeyEvent *) override;
private:
    qreal xOfFrame(int frame) const;
    int hit(const QPointF &p) const;
    TimelineView *timeline_ = nullptr;
    QString row_;
    QJsonArray spawns_;
    QStringList names_;
    int selected_ = -1, dragging_ = -1, dragFrame_ = 0;
    qreal grab_ = 0; // where inside the chip the press landed
};

class ProjectilesPanel : public QWidget {
    Q_OBJECT
public:
    explicit ProjectilesPanel(QWidget *parent = nullptr);
    void setData(const QJsonArray &articles, const QJsonArray &spawns, const QString &row);
    int selectedArticle() const;
    void selectArticle(int index);
    QStringList articleNames() const;
signals:
    void editRequested(const QString &command, const QJsonObject &args);
    void addSpawnRequested(int article);
private:
    void rebuildFields();
    void setOp(const QString &path, const QJsonValue &value);
    QJsonObject current() const;
    QJsonArray articles_, spawns_;
    QString row_;
    bool feedback_ = false;
    QListWidget *list_, *spawnList_;
    QWidget *form_;
    QMap<QString, QWidget *> editors_;
    QTableWidget *boxes_;
    QLabel *note_;
    QPushButton *addBox_, *removeBox_, *addSpawn_, *removeSpawn_, *addArticle_, *removeArticle_;
};
} // namespace wb
