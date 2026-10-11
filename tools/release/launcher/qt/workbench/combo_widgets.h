#pragma once
// The combo graph in the Workbench (geno.md 25): a lane per outgoing route under the move timeline, the Combo
// inspector tab (the move's routes with editable fields and the XV2 source text), and the string map (moves as
// nodes, routes as edges). Like the projectile widgets they only emit command requests (edit_route, add_route,
// delete_route, edit_string, ...): the window runs them through the session like every other edit.
#include "combo_model.h"
#include <QColor>
#include <QJsonArray>
#include <QJsonObject>
#include <QWidget>

class QCheckBox;
class QComboBox;
class QLabel;
class QLineEdit;
class QListWidget;
class QPlainTextEdit;
class QPushButton;
class QSpinBox;

namespace wb {
class TimelineView;

// Colour by input class (light heavy special jump grab shield none); Blender's route markers use the same table.
QColor comboInputColour(const QString &inputClass);

class RouteLanes : public QWidget {
    Q_OBJECT
public:
    explicit RouteLanes(QWidget *parent = nullptr);
    void setTimeline(TimelineView *timeline);
    // All routes of the project; the lanes show those that leave `row` (by name or motion token).
    void setRoutes(const QString &row, const QStringList &tokens, const QJsonArray &routes);
    int laneCount() const { return lanes_.size(); }
    int routeIndexAt(int lane) const;
    QRectF barRect(int lane) const;            // lane coordinates; the dragged position while dragging
    int selectedRoute() const { return selected_; }
    void selectRoute(int routeIndex);
    int laneHeight() const { return 24; }
    QSize sizeHint() const override;
    QSize minimumSizeHint() const override;
signals:
    void editRequested(const QString &command, const QJsonObject &args);
    void routeSelected(int routeIndex);
protected:
    void paintEvent(QPaintEvent *) override;
    void mousePressEvent(QMouseEvent *) override;
    void mouseMoveEvent(QMouseEvent *) override;
    void mouseReleaseEvent(QMouseEvent *) override;
    void keyPressEvent(QKeyEvent *) override;
    bool event(QEvent *) override;
private:
    enum class Grab { None, Move, Start, End };
    qreal xOfBoundary(int boundary) const;
    int boundaryAt(qreal x) const;
    int endBoundary(const QJsonObject &route, int hi) const;
    QPair<int, int> shown(int lane) const;     // window [lo, hi] as drawn (the drag position while dragging)
    int laneAt(const QPointF &p) const;
    QString tipFor(int lane) const;
    TimelineView *timeline_ = nullptr;
    QString row_;
    QJsonArray lanes_;                         // the routes drawn, each with "index"
    int selected_ = -1, dragLane_ = -1, dragLo_ = 1, dragHi_ = 0, pressBoundary_ = 0, originLo_ = 1, originHi_ = 0;
    Grab grab_ = Grab::None;
};

class StringMap : public QWidget {
    Q_OBJECT
public:
    explicit StringMap(QWidget *parent = nullptr);
    // `moves`: the names the Moves list has, so other nodes (geno: states) draw dimmed and cannot be selected.
    void setGraph(const QJsonArray &routes, const QJsonArray &strings, const QStringList &moves);
    void setSelectedMove(const QString &name);
    void setActiveString(int stringIndex);     // its steps are drawn bold; -1 none
    QRectF nodeRect(const QString &name) const;
    int nodeCount() const { return graph_.nodes.size(); }
    int edgeCount() const { return graph_.edges.size(); }
    QSize sizeHint() const override;
    QSize minimumSizeHint() const override { return {160, 120}; }
signals:
    void moveClicked(const QString &name);     // a node that has a row in the Moves list
    void nodeClicked(const QString &name);     // any node
protected:
    void paintEvent(QPaintEvent *) override;
    void mousePressEvent(QMouseEvent *) override;
private:
    QRectF rectOf(int node) const;
    QString nodeAt(const QPointF &p) const;
    ComboGraph graph_;
    QJsonArray routes_, strings_;
    QStringList moves_;
    QString selected_;
    int active_ = -1;
};

class ComboPanel : public QWidget {
    Q_OBJECT
public:
    explicit ComboPanel(QWidget *parent = nullptr);
    void setData(const QJsonArray &routes, const QJsonArray &strings, const QJsonObject &meta, const QStringList &moves,
                 const QString &row, const QStringList &tokens, bool declared);
    int selectedRoute() const;                 // file index of the route in the form, -1 none
    void selectRoute(int routeIndex);
    int selectedString() const;
    StringMap *stringMap() const { return map_; }
signals:
    void editRequested(const QString &command, const QJsonObject &args);
    void moveRequested(const QString &name);
    void playStringRequested(int stringIndex);
    void routeSelected(int routeIndex);
private:
    void rebuildList();
    void rebuildForm();
    void rebuildStrings();
    void edit(const QString &key, const QJsonValue &value);
    void editWindow();
    QJsonObject current() const;
    QJsonArray routes_, strings_;
    QJsonObject meta_;
    QStringList moves_, tokens_;
    QString row_;
    bool declared_ = false, feedback_ = false;
    QLabel *note_, *moveNote_;
    QCheckBox *all_;
    QListWidget *list_, *stringList_;
    QWidget *form_;
    QLineEdit *name_, *from_, *to_, *stepsEdit_, *stringName_;
    QComboBox *input_, *dir_, *on_, *where_;
    QSpinBox *lo_, *hi_, *buffer_, *priority_, *kiCost_;
    QPlainTextEdit *source_;
    QPushButton *add_, *remove_, *addString_, *removeString_, *play_;
    StringMap *map_;
};
} // namespace wb
