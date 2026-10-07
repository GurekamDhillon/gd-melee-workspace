#include "window.h"
#include "kit.h"
#include "graphics.h"
#include <QGuiApplication>
#include <QDateTime>
#include <QApplication>
#include <QCheckBox>
#include <QClipboard>
#include <QCloseEvent>
#include <QComboBox>
#include <QDesktopServices>
#include <QDir>
#include <QFileDialog>
#include <QFile>
#include <QAbstractButton>
#include <QFileInfo>
#include <QFormLayout>
#include <QGridLayout>
#include <QGroupBox>
#include <QHeaderView>
#include <QInputDialog>
#include <QLabel>
#include <QLineEdit>
#include <QMessageBox>
#include <QMenu>
#include <QMouseEvent>
#include <QPainter>
#include <QPalette>
#include <QPushButton>
#include <QRegularExpression>
#include <QPlainTextEdit>
#include <QScrollArea>
#include <QShortcut>
#include <QSlider>
#include <QStatusBar>
#include <QTableWidget>
#include <QStackedWidget>
#include <QTimer>
#include <QUrl>
#include <QVBoxLayout>
#include <functional>
#include <tuple>
#include <algorithm>

namespace launcher {
#ifdef Q_OS_LINUX
static QString osRelease() { QFile f("/etc/os-release"); return f.open(QIODevice::ReadOnly) ? QString::fromUtf8(f.read(16384)) : QString(); }
#endif
bool spanish = false;
QString t(const char *en, const char *es) { return QString::fromUtf8(spanish ? es : en); }
static QPushButton *button(QBoxLayout *layout, const QString &text, const std::function<void()> &action) {
    auto *w = new kit::Button(text); layout->addWidget(w); QObject::connect(w, &QPushButton::clicked, w, action); return w;
}
// Layout constants with no token: the three measurements of the Atlas launcher concept
// (menu/concepts/reunification-2026-10-06/c-atlas/screens_b.py, s17): rail 204 wide, trail 34 high, main padding 18 top and bottom.
// The left column (420) is the primary's maximum width, applied where the tabs are built.
constexpr int kDetailsRole = Qt::UserRole + 10;        // a mod item: description, version, requires, conflicts
constexpr int kRailWidth = 204, kTrailHeight = 34, kMainPadY = 18, kPrimaryWidth = 420, kExplainerMin = 240;

// The only way a label gets a colour: a token, through the palette.
static QLabel *capLabel(const QString &text, atlas::Role role, const char *colourToken = "ivory") {
    auto *w = new QLabel(text); w->setTextFormat(Qt::PlainText); w->setFont(atlas::font(role));
    QPalette pal = w->palette(); pal.setColor(QPalette::WindowText, atlas::colour(colourToken)); w->setPalette(pal);
    return w;
}
// The strip's mark: the concept's own diamond (parts.py defs: ember, ground, ivory), drawn from tokens.
class MarkWidget : public QWidget {
public:
    explicit MarkWidget(int size = 18) : QWidget(nullptr) { setFixedSize(size, size); }
protected:
    void paintEvent(QPaintEvent *) override {
        QPainter p(this); p.setPen(Qt::NoPen); p.setRenderHint(QPainter::Antialiasing, false);
        const qreal s = width() / 24.0;
        auto diamond = [&](qreal r, const QColor &c) { p.setBrush(c); p.drawPolygon(QPolygonF{{12 * s, (12 - r) * s}, {(12 + r) * s, 12 * s}, {12 * s, (12 + r) * s}, {(12 - r) * s, 12 * s}}); };
        diamond(11, atlas::colour("ember")); diamond(7, atlas::colour("ground")); diamond(4, atlas::colour("ivory"));
    }
};
static QString versionText(const QString &appDir) {
    try { return readText(appDir + "/version.txt", 16384).section(QChar('\n'), 0, 0).trimmed(); } catch (...) {}
    return QString("dev");
}
// A one-line label that elides with an ellipsis instead of growing the window (a 40-character disc name, a long path).
class ElidedLabel : public QLabel {
public:
    ElidedLabel(const QString &text, atlas::Role role, const char *colourToken = "ivory") : QLabel(text) {
        setTextFormat(Qt::PlainText); setFont(atlas::font(role));
        QPalette pal = palette(); pal.setColor(QPalette::WindowText, atlas::colour(colourToken)); setPalette(pal);
        setSizePolicy(QSizePolicy::Ignored, QSizePolicy::Fixed);
    }
    QSize sizeHint() const override { return {int(fontMetrics().horizontalAdvance(text())), fontMetrics().height()}; }
    QSize minimumSizeHint() const override { return {8, fontMetrics().height()}; }
protected:
    void paintEvent(QPaintEvent *) override {
        QPainter p(this); p.setFont(font()); p.setPen(palette().color(QPalette::WindowText));
        p.drawText(rect(), Qt::AlignLeft | Qt::AlignVCenter, atlas::fit(QFontMetricsF(font()), text(), width()));
    }
};
// A wrapped paragraph in a body role.
static QLabel *paragraph(const QString &text, atlas::Role role = atlas::Role::Body14, const char *colourToken = "ivory") {
    auto *w = capLabel(text, role, colourToken); w->setWordWrap(true); w->setAlignment(Qt::AlignLeft | Qt::AlignTop);
    w->setSizePolicy(QSizePolicy::Ignored, QSizePolicy::Minimum);
    return w;
}
// The explainer (place 3): WHAT, WITH, FROM in this order: a kicker, a title, a sentence, a short facts list, and a bottom line.
class ExplainerPane : public kit::Pane {
public:
    explicit ExplainerPane(const QString &kicker) : kit::Pane() {
        setObjectName("atlasExplainer");
        auto *l = new QVBoxLayout(body()); l->setContentsMargins(0, 0, 0, 0); l->setSpacing(9);
        kicker_ = new ElidedLabel(kicker.toUpper(), atlas::Role::Cap12, "jade"); l->addWidget(kicker_);
        title_ = new ElidedLabel(QString(), atlas::Role::Title); l->addWidget(title_);
        what_ = paragraph(QString()); l->addWidget(what_);
        facts_ = new QGridLayout; facts_->setHorizontalSpacing(atlas::px("s2")); facts_->setVerticalSpacing(3); facts_->setColumnMinimumWidth(0, 64); facts_->setColumnStretch(1, 1); l->addLayout(facts_);
        l->addStretch(1);
        more_ = new QVBoxLayout; more_->setSpacing(atlas::px("s2")); l->addLayout(more_);
    }
    QLabel *title() const { return title_; }
    QLabel *what() const { return what_; }
    QVBoxLayout *more() const { return more_; }
    QLabel *addFact(const QString &name, const QString &value = {}) {
        const int row = facts_->rowCount();
        facts_->addWidget(new ElidedLabel(name.toUpper(), atlas::Role::Cap12, "muted"), row, 0);
        auto *v = new ElidedLabel(value, atlas::Role::Body14, "text2"); facts_->addWidget(v, row, 1); return v;
    }
private:
    ElidedLabel *kicker_, *title_; QLabel *what_; QGridLayout *facts_; QVBoxLayout *more_;
};
// A settings row: a label on the left, a control on the right; focus (the toggle's or the slider's) lifts the whole row.
class OptionRow : public QWidget {
public:
    // stacked: the label above and the control below, for a control that needs the row's width (a combo box)
    OptionRow(const QString &label, QWidget *control, QWidget *focusWidget, bool clickToggles, bool stacked = false) : QWidget(nullptr), focus_(focusWidget), click_(clickToggles ? qobject_cast<QAbstractButton *>(control) : nullptr), height_(stacked ? kStackedHeight : kRowHeight) {
        setFixedHeight(height_ + 2); setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
        if (stacked) {
            auto *l = new QVBoxLayout(this); l->setContentsMargins(atlas::px("s3"), 2 + 4, atlas::px("s3"), atlas::px("ch-xs") + 4); l->setSpacing(2);
            l->addWidget(new ElidedLabel(label, atlas::Role::Body12, "muted")); l->addWidget(control);
        } else {
            auto *l = new QHBoxLayout(this); l->setContentsMargins(atlas::px("s3"), 2, atlas::px("s3"), atlas::px("ch-xs")); l->setSpacing(atlas::px("s3"));
            l->addWidget(new ElidedLabel(label, atlas::Role::Row16, "text2"), 1); l->addWidget(control, 0, Qt::AlignVCenter);
        }
        focus_->installEventFilter(this);
    }
protected:
    bool eventFilter(QObject *o, QEvent *e) override { if (o == focus_ && (e->type() == QEvent::FocusIn || e->type() == QEvent::FocusOut)) update(); return QWidget::eventFilter(o, e); }
    void mousePressEvent(QMouseEvent *e) override { if (click_ && e->button() == Qt::LeftButton) { click_->setFocus(Qt::MouseFocusReason); click_->click(); } else QWidget::mousePressEvent(e); }
    void paintEvent(QPaintEvent *) override {
        QPainter p(this); p.setRenderHint(QPainter::Antialiasing, false);
        const bool focus = focus_->hasFocus();
        const QRectF base(0, 2, width(), height_), r = atlas::lifted(base, focus);
        kit::paintPlate(p, r, focus ? atlas::colour("lift") : atlas::colour("plate2"), focus ? atlas::colour("ember") : atlas::colour("edge2"), atlas::px("ch-xs"), atlas::px("ch-s"));
        if (focus) p.fillRect(atlas::tick(r.adjusted(0, 0, 0, -atlas::px("ch-xs"))), atlas::colour("ember"));
    }
private:
    static constexpr int kRowHeight = 34, kStackedHeight = 56;             // the mockup's option row; disc rows are the 46 tall one
    QWidget *focus_; QAbstractButton *click_; int height_;
};
// An icon and a line of text: the "ready" line above the Play button.
class NoteLine : public QWidget {
public:
    NoteLine() : QWidget(nullptr) { setFixedHeight(24); setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed); }
    void set(const QString &icon, const QString &text) { icon_ = icon; text_ = text; setToolTip(text); update(); }
protected:
    void paintEvent(QPaintEvent *) override {
        QPainter p(this); kit::paintIcon(p, icon_, QRectF(0, 3, 18, 18), atlas::colour("jade"));
        const QFont f = atlas::font(atlas::Role::Body14); p.setFont(f); p.setPen(atlas::colour("text2"));
        p.drawText(QRectF(26, 0, width() - 26, height()), Qt::AlignLeft | Qt::AlignVCenter, atlas::fit(QFontMetricsF(f), text_, width() - 26));
    }
private:
    QString icon_, text_;
};
// A combo box that draws its own arrow (a flat token-coloured triangle); the style sheet leaves the drop-down empty.
class Combo : public QComboBox {
protected:
    void paintEvent(QPaintEvent *e) override {
        QComboBox::paintEvent(e);
        QPainter p(this); p.setRenderHint(QPainter::Antialiasing, false); p.setPen(Qt::NoPen); p.setBrush(atlas::colour(isEnabled() ? "ivory" : "muted"));
        const qreal cx = width() - 16, cy = (height() - 2) / 2.0;
        p.drawPolygon(QPolygonF{{cx - 5, cy - 2}, {cx + 5, cy - 2}, {cx, cy + 4}});
    }
};
// A settings row whose control is a combo box: compact (it must fit the 34 px row) and sized by a short minimum length,
// never by its longest item, so a long GPU name cannot push the pane wider than its column.
static QComboBox *rowCombo(QBoxLayout *into, const QString &title) {
    auto *w = new Combo; w->setProperty("inRow", true); w->setAccessibleName(title);
    w->setSizeAdjustPolicy(QComboBox::AdjustToMinimumContentsLengthWithIcon); w->setMinimumContentsLength(8);
    w->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
    into->addWidget(new OptionRow(title, w, w, false, true)); return w;
}
// The disc and mod lists: the rows are painted by the delegate; with no disc yet the list says so in a hatched frame.
class RowTable : public QTableWidget {
public:
    using QTableWidget::QTableWidget;
    QString placeholder;
protected:
    void paintEvent(QPaintEvent *e) override {
        QTableWidget::paintEvent(e);
        if (rowCount() > 0) return;
        QPainter p(viewport()); p.setRenderHint(QPainter::Antialiasing, false);
        const QRectF r = QRectF(viewport()->rect()).adjusted(0, 2, 0, -3);
        kit::paintPlate(p, r, atlas::colour("ground2"), atlas::colour("edge2"), atlas::px("ch-xs"), atlas::px("ch-s"));
        kit::paintHatch(p, atlas::plate(r.adjusted(0, 0, 0, -atlas::px("ch-xs")), atlas::px("ch-s")), atlas::colour("line"));
        const QFont f = atlas::font(atlas::Role::Body14); p.setFont(f); p.setPen(atlas::colour("muted"));
        p.drawText(r.adjusted(atlas::px("s3"), 0, -atlas::px("s3"), -atlas::px("ch-xs")), Qt::AlignCenter | Qt::TextWordWrap, placeholder);
    }
};
// The one place a stylesheet is built: what Qt draws itself (combo boxes, edits, scroll bars, tips, menus, dialogs).
// Every colour is a token: "@name@" is replaced by atlas::colour(name).
static QString themed(const QString &css) {
    static const QRegularExpression re("@([a-z0-9-]+)@");
    QString out; int last = 0; auto it = re.globalMatch(css);
    while (it.hasNext()) { auto m = it.next(); out += css.mid(last, m.capturedStart() - last) + atlas::colour(m.captured(1)).name(); last = m.capturedEnd(); }
    return out + css.mid(last);
}
static QString atlasStyleSheet() {
    return themed(QString(R"(
      QMainWindow, QStackedWidget, QScrollArea { background: transparent; border: none; }
      QLabel { background: transparent; }
      QTableWidget { background: transparent; border: none; outline: 0; }
      QTableWidget::item { border: none; padding: 0; }
      QComboBox, QLineEdit { background: @plate2@; color: @ivory@; border: 0; border-bottom: 3px solid @edge2@; padding: 5px 12px; min-height: 22px; selection-background-color: @lift@; selection-color: @ivory@; }
      QComboBox[inRow="true"] { padding: 1px 10px; min-height: 18px; border-bottom-width: 2px; }
      QComboBox:focus, QLineEdit:focus { background: @lift@; border-bottom-color: @ember@; }
      QComboBox::drop-down { border: 0; width: 24px; }
      QComboBox::down-arrow { image: none; width: 0; height: 0; }
      QComboBox QAbstractItemView { background: @plate@; color: @ivory@; selection-background-color: @lift@; selection-color: @ivory@; border: 0; outline: 0; }
      QPlainTextEdit { background: @ground2@; color: @text2@; border: 0; border-bottom: 3px solid @edge2@; selection-background-color: @lift@; selection-color: @ivory@; }
      QSlider::groove:horizontal { height: 4px; background: @line2@; }
      QSlider::sub-page:horizontal { background: @jade@; }
      QSlider::handle:horizontal { width: 10px; margin: -8px 0; background: @ivory@; border: 0; }
      QSlider::handle:horizontal:focus { background: @ember@; }
      QScrollBar:vertical { background: @ground2@; width: 8px; margin: 0; }
      QScrollBar::handle:vertical { background: @line2@; min-height: 32px; }
      QScrollBar::handle:vertical:hover { background: @muted@; }
      QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
      QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
      QStatusBar { background: @ground@; color: @muted@; padding: 2px 24px; }
      QStatusBar::item { border: none; }
      QToolTip { background: @lift@; color: @ivory@; border: 0; border-bottom: 3px solid @edge@; padding: 6px 10px; }
      QMenu { background: @plate@; color: @ivory@; border: 0; border-bottom: 3px solid @edge@; padding: 4px; }
      QMenu::item { padding: 6px 24px; }
      QMenu::item:selected { background: @lift@; color: @ivory@; }
      QMenu::separator { height: 1px; background: @line@; margin: 4px 0; }
      QDialog, QMessageBox, QInputDialog { background: @plate@; }
      QDialog QLabel, QMessageBox QLabel { color: @ivory@; }
      QDialog QPushButton { background: @plate2@; color: @ivory@; border: 0; border-bottom: 3px solid @edge2@; padding: 8px 20px; min-width: 64px; }
      QDialog QPushButton:focus, QDialog QPushButton:hover { background: @lift@; border-bottom-color: @ember@; }
    )"));
}
void applyTheme() {
    atlas::initialize();
    QApplication::setFont(atlas::font(atlas::Role::Body14));
    QPalette pal;
    pal.setColor(QPalette::Window, atlas::colour("ground")); pal.setColor(QPalette::WindowText, atlas::colour("ivory"));
    pal.setColor(QPalette::Base, atlas::colour("plate")); pal.setColor(QPalette::AlternateBase, atlas::colour("plate2"));
    pal.setColor(QPalette::Text, atlas::colour("ivory")); pal.setColor(QPalette::Button, atlas::colour("plate2")); pal.setColor(QPalette::ButtonText, atlas::colour("ivory"));
    pal.setColor(QPalette::Highlight, atlas::colour("lift")); pal.setColor(QPalette::HighlightedText, atlas::colour("ivory"));
    pal.setColor(QPalette::ToolTipBase, atlas::colour("lift")); pal.setColor(QPalette::ToolTipText, atlas::colour("ivory"));
    pal.setColor(QPalette::Disabled, QPalette::Text, atlas::colour("muted")); pal.setColor(QPalette::Disabled, QPalette::ButtonText, atlas::colour("muted"));
    QApplication::setPalette(pal);
    qApp->setStyleSheet(atlasStyleSheet());
}
Window::Window(QString app, QString user, Settings settings)
    : appDir_(std::move(app)), userDir_(std::move(user)), settings_(std::move(settings)) {
    setObjectName("atlasWindow"); setWindowTitle("GD's Melee"); resize(960, 640); setMinimumSize(900, 600);
    // E0 ground, then the four places: trail (top), the rail and the tab bodies (primary + explainer), keys (bottom).
    auto *root = new QWidget; root->setObjectName("atlasGround");
    root->setAutoFillBackground(true); { QPalette pal = root->palette(); pal.setColor(QPalette::Window, atlas::colour("ground")); root->setPalette(pal); }
    auto *col = new QVBoxLayout(root); col->setContentsMargins(0, 0, 0, 0); col->setSpacing(0);
    auto *trail = new QWidget; trail->setObjectName("atlasTrail"); trail->setFixedHeight(kTrailHeight);
    trail->setAutoFillBackground(true); { QPalette pal = trail->palette(); pal.setColor(QPalette::Window, atlas::colour("ground")); trail->setPalette(pal); }
    auto *th = new QHBoxLayout(trail); th->setContentsMargins(atlas::px("s3"), 0, atlas::px("s3"), 0); th->setSpacing(atlas::px("s2"));
    th->addWidget(new MarkWidget); th->addWidget(capLabel("GD'S MELEE", atlas::Role::Cap16)); th->addWidget(capLabel(t("LAUNCHER", "LANZADOR"), atlas::Role::Cap16, "muted")); th->addStretch();
    th->addWidget(capLabel(versionText(appDir_), atlas::Role::Body14, "muted"));
    col->addWidget(trail);
    auto *body = new QHBoxLayout; body->setContentsMargins(0, 0, 0, 0); body->setSpacing(0); col->addLayout(body, 1);
    rail_ = new kit::TabRail({t("PLAY", "JUGAR"), t("MODS", "MODS"), t("DIAGNOSTICS", "DIAGNÓSTICO"), t("ABOUT", "ACERCA DE")});
    rail_->setObjectName("atlasRail"); rail_->setFixedWidth(kRailWidth); rail_->setIcons({"right", "mods", "data", "star"}); body->addWidget(rail_);
    auto *main = new QVBoxLayout; main->setContentsMargins(atlas::px("s5"), kMainPadY, atlas::px("s5"), kMainPadY); main->setSpacing(atlas::px("s3")); body->addLayout(main, 1);
    pageHeading_ = capLabel(QString(), atlas::Role::Title);  pageSub_ = capLabel(QString(), atlas::Role::Body14, "muted");
    auto *hd = new QHBoxLayout; hd->setSpacing(atlas::px("s3")); hd->addWidget(pageHeading_); hd->addWidget(pageSub_, 1, Qt::AlignBottom); main->addLayout(hd);
    tabs_ = new QStackedWidget; tabs_->setObjectName("atlasTabs");
    tabs_->addWidget(playTab()); tabs_->addWidget(modsTab()); tabs_->addWidget(diagnosticsTab()); tabs_->addWidget(aboutTab()); main->addWidget(tabs_, 1);
    keys_ = new QWidget; keys_->setObjectName("atlasKeys"); keys_->setFixedHeight(26); main->addWidget(keys_);
    setCentralWidget(root);
    const QStringList headings{t("Play", "Jugar"), t("Mods", "Mods"), t("Diagnostics", "Diagnóstico"), t("About", "Acerca de")};
    const QStringList subs{t("Pick a disc, then play.", "Pick a disc, then play."), t("Custom content, applied at the next launch.", "Custom content, applied at the next launch."),
                           t("Logs, graphics and reports.", "Logs, graphics and reports."), t("This launcher and what it uses.", "This launcher and what it uses.")};
    connect(rail_, &kit::TabRail::currentChanged, this, [this, headings, subs](int index) {
        tabs_->setCurrentIndex(index); pageHeading_->setText(headings[index].toUpper()); pageSub_->setText(subs[index]); setKeys(index);
        auto *f = QApplication::focusWidget();                       // never leave focus on a control that is now hidden
        if (!f || !f->isVisible() || (tabs_->isAncestorOf(f) && !tabs_->currentWidget()->isAncestorOf(f))) rail_->setFocus();
    });
    pageHeading_->setText(headings[0].toUpper()); pageSub_->setText(subs[0]); setKeys(0);
    for (int i = 0; i < 4; ++i) { auto *s = new QShortcut(QKeySequence(Qt::CTRL | (Qt::Key_1 + i)), this); connect(s, &QShortcut::activated, this, [this, i] { rail_->setCurrent(i); }); }
    { auto *s = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_M), this); connect(s, &QShortcut::activated, this, [this] { selectMods(); }); }
    refreshDiscs(); guarded([&] { refreshMods(); });
#ifdef Q_OS_LINUX
    graphicsTimeout_ = new QTimer(this); graphicsTimeout_->setSingleShot(true);
    connect(graphicsTimeout_, &QTimer::timeout, this, [this] { graphicsTimedOut_ = true; graphicsProcess_.kill(); });
    connect(&graphicsProcess_, &QProcess::readyReadStandardOutput, this, [this] {
        graphicsOutput_ += graphicsProcess_.readAllStandardOutput();
        if (graphicsOutput_.size() > 1024 * 1024) { graphicsOutput_.truncate(1024 * 1024); graphicsProcess_.kill(); }
    });
    connect(&graphicsProcess_, &QProcess::readyReadStandardError, this, [this] {
        graphicsErrors_ += graphicsProcess_.readAllStandardError(); graphicsErrors_ = graphicsErrors_.right(64 * 1024);
    });
    connect(&graphicsProcess_, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this, [this](int code, QProcess::ExitStatus status) { finishGraphics(status == QProcess::NormalExit ? code : -1); });
    connect(&graphicsProcess_, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) { if (error == QProcess::FailedToStart) { graphicsErrors_ = graphicsProcess_.errorString().toUtf8(); finishGraphics(-1); } });
#endif
    connect(&process_, &QProcess::started, this, [this] { diag_.spawn.started = true; });
    connect(&process_, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
        if (error != QProcess::FailedToStart) return;
        auto &sp = diag_.spawn; sp.started = false; sp.processError = int(error); sp.errorString = process_.errorString(); sp.finished = false;
        QStringList env; for (const auto &k : diag_.spec.environment.keys()) env << k + "=" + diag_.spec.environment.value(k);
        sp.execProbe = execProbe(sp.program, env);
        play_->setEnabled(true); updatePlayState(); finishLaunchReport(true);
    });
    connect(&process_, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this, [this](int code, QProcess::ExitStatus status) {
        play_->setEnabled(true); updatePlayState();
        auto &sp = diag_.spawn; sp.finished = true; sp.exitCode = code; sp.crashed = status == QProcess::CrashExit; sp.elapsedMs = launchClock_.elapsed();
        // Qt 6 reports the terminating signal number as exitCode() for a CrashExit on Unix (checked on 6.8).
        sp.signal = sp.crashed && code >= 1 && code <= 64 ? signalName(code) : QString();
        auto crash = latestCrash(runDir_);
        const bool failed = status == QProcess::CrashExit || code != 0 || !crash.isEmpty();
        finishLaunchReport(failed);
        if (!failed) { if (quitting_ || settings_.flag("close_on_play")) QApplication::quit(); else statusBar()->showMessage(t("Game closed.", "Juego cerrado.")); }
    });
}
void Window::setKeys(int tab) {
    delete keys_->layout();
    qDeleteAll(keys_->findChildren<QWidget *>(QString(), Qt::FindDirectChildrenOnly));
    auto *l = new QHBoxLayout(keys_); l->setContentsMargins(0, 0, 0, 0); l->setSpacing(atlas::px("s1"));
    auto hint = [&](const QStringList &chips, const QString &text) {
        for (const auto &c : chips) l->addWidget(new kit::KeyChip(c));
        auto *w = capLabel(text, atlas::Role::Body12, "muted"); l->addWidget(w); l->addSpacing(atlas::px("s3"));
    };
    switch (tab) {
    case 0: hint({"Enter"}, t("to play", "to play")); hint({"Ctrl", "M"}, t("mods", "mods")); break;
    case 1: hint({"Space"}, t("turns a mod on or off", "turns a mod on or off")); hint({"Ctrl", "M"}, t("mods", "mods")); break;
    case 2: hint({"Tab"}, t("moves between controls", "moves between controls")); break;
    default: hint({"Tab"}, t("moves between controls", "moves between controls")); break;
    }
    hint({"Ctrl", "1-4"}, t("switch tab", "switch tab")); l->addStretch();
}
DiagContext Window::diagContext(bool full) const {
    DiagContext c = diag_; c.appDir = appDir_; c.userDir = userDir_; c.runDir = runDir_; c.full = full;
    c.platform = QGuiApplication::platformName(); c.launcherExe = QCoreApplication::applicationFilePath();
    c.graphicsDevice = settings_.option("graphics_device", "auto");
    c.discPaths.clear(); for (const auto &d : settings_.discs) c.discPaths << d.path;
    return c;
}
void Window::finishLaunchReport(bool showDialog) {
    // The slow probes (lspci, vulkaninfo) only run for a failure; a clean exit keeps the quick report.
    auto ctx = diagContext(showDialog); ctx.finished = true;
    auto report = writeDiagnostics(ctx);
    if (!showDialog) return;
    show(); quitting_ = false;
    QString extra;
#ifdef Q_OS_LINUX
    extra = graphicsStartupFailure(runDir_, osRelease());
#endif
    showLaunchFailure(report, extra);
}
void Window::showLaunchFailure(const DiagResult &report, const QString &extra) {
    const auto &v = report.verdict;
    QString text = t("The game could not start or stopped unexpectedly.", "The game could not start or stopped unexpectedly.") + "\n\n" + v.line() + "\n" + v.message;
    if (!v.hint.isEmpty()) text += "\n\n" + t("Hint: ", "Hint: ") + v.hint;
    text += "\n\n" + t("A diagnostics report was saved. Copy it and send it when asking for help.", "A diagnostics report was saved. Copy it and send it when asking for help.");
    QMessageBox dialog(QMessageBox::Warning, t("Game stopped", "El juego se ha detenido"), text, QMessageBox::NoButton, this);
    dialog.setTextFormat(Qt::PlainText);
    dialog.setDetailedText(t("Report: ", "Report: ") + report.latestPath + "\n" + t("Logs are available here:\n", "Registros disponibles aquí:\n") + runDir_ + (extra.isEmpty() ? QString() : "\n\n" + extra));
    auto *copy = dialog.addButton(t("Copy diagnostics", "Copy diagnostics"), QMessageBox::ActionRole);
    auto *open = dialog.addButton(t("Open log folder", "Abrir carpeta de registros"), QMessageBox::ActionRole);
    dialog.addButton(QMessageBox::Ok);
    for (;;) {
        dialog.exec();
        if (dialog.clickedButton() == copy) { QApplication::clipboard()->setText(report.text); statusBar()->showMessage(t("Launch diagnostics copied.", "Launch diagnostics copied.")); }
        else if (dialog.clickedButton() == open) openPath(diagnosticsDir(userDir_));
        else break;
    }
}
void Window::runDiagnosticsOnly() { guarded([&] {
    DiagContext c = diagContext(true); c.spawn = {}; c.haveSpec = false; c.finished = true; c.runDir.clear();
    statusBar()->showMessage(t("Running diagnostics...", "Running diagnostics...")); QApplication::setOverrideCursor(Qt::WaitCursor);
    auto report = writeDiagnostics(c); QApplication::restoreOverrideCursor();
    showLaunchFailure(report);
}); }
void Window::copyDiagnostics() { guarded([&] {
    auto path = diagnosticsDir(userDir_) + "/launch-diagnostics.txt";
    if (!QFile::exists(path)) { statusBar()->showMessage(t("No launch diagnostics yet. Start the game or run diagnostics first.", "No launch diagnostics yet. Start the game or run diagnostics first.")); return; }
    QApplication::clipboard()->setText(readText(path, 4 * 1024 * 1024)); statusBar()->showMessage(t("Launch diagnostics copied.", "Launch diagnostics copied."));
}); }
void Window::guarded(const std::function<void()> &action) {
    try { action(); } catch (const std::exception &e) { QMessageBox::warning(this, t("Could not complete the action", "No se pudo completar la acción"), QString::fromUtf8(e.what())); }
}
void Window::save() { settings_.save(userDir_); }
void Window::openPath(const QString &path) {
    if (!QDesktopServices::openUrl(QUrl::fromLocalFile(path))) QMessageBox::warning(this, t("Open folder or file", "Abrir carpeta o archivo"), path);
}
int Window::selectedDisc() const { int row = discs_->currentRow(); return row >= 0 && row < settings_.discs.size() ? row : -1; }
void Window::refreshDiscs(const QString &id) {
    discs_->setRowCount(settings_.discs.size());
    int selected = settings_.defaultIndex();
    for (int row = 0; row < settings_.discs.size(); ++row) {
        const auto &d = settings_.discs[row];
        QStringList values{d.name, d.kind, d.path};
        for (int col = 0; col < values.size(); ++col) { auto *item = new QTableWidgetItem(values[col]); item->setToolTip(values[col]); discs_->setItem(row, col, item); }
        auto *item = discs_->item(row, 0); const bool present = QFileInfo::exists(d.path);
        item->setData(kit::SubRole, (d.id == settings_.defaultId ? t("Default", "Default") + " - " : QString()) + QFileInfo(d.path).fileName());
        item->setData(kit::TagTextRole, present ? t("Ready", "Ready") : t("Missing", "Missing"));
        item->setData(kit::TagToneRole, present ? int(kit::Tag::Jade) : int(kit::Tag::Rose));
        item->setData(kit::BadgeRole, d.kind.left(2).toUpper());
        discs_->setRowHeight(row, kit::RowDelegate::rowHeight());
        if (d.id == id) selected = row;
    }
    if (selected >= 0) discs_->selectRow(selected);
    if (auto *library = findChild<kit::Pane *>("atlasLibrary")) library->setCount(QString::number(settings_.discs.size()) + " " + (settings_.discs.size() == 1 ? t("disc", "disc") : t("discs", "discs")));
    showSelectedDisc();
}
// The explainer and the Play block follow the selection; the Play button says why it can or cannot act.
void Window::showSelectedDisc() {
    const int i = selectedDisc();
    auto *note = static_cast<NoteLine *>(playNote_);
    if (i < 0) {
        discTitle_->setText(t("Choose your disc", "Elige tu disco"));
        discDetails_->setText(t("Add your own Melee NTSC-U 1.02 ISO, Akaneia, or ACE disc image. No game data is included.", "Añade tu propia ISO de Melee NTSC-U 1.02, Akaneia o ACE. No se incluyen datos del juego."));
        if (note) note->set("plus", t("Add a disc to begin.", "Add a disc to begin."));
    } else {
        const auto &d = settings_.discs[i];
        discTitle_->setText(d.name.toUpper());
        discDetails_->setText(t("The game starts from the selected disc.", "The game starts from the selected disc.") + " " + t("Saves stay with this disc, even when you rename it or change its ISO.", "Las partidas guardadas siguen con este disco aunque lo renombres o cambies su ISO."));
        if (note) note->set("check", t("Ready to play.", "Ready to play."));
    }
    updatePlayState();
}
void Window::updatePlayState() {
    if (!play_) return;
    play_->setToolTip(selectedDisc() < 0 ? t("Add a disc first.", "Add a disc first.") : t("Starts the selected disc.", "Starts the selected disc."));
}
QWidget *Window::playTab() {
    auto *page = new QWidget; auto *layout = new QHBoxLayout(page); layout->setContentsMargins(0, 0, 0, 0); layout->setSpacing(atlas::px("s3"));
    // primary (left, at most 420 wide): the Disc library, then the Options
    auto *leftColumn = new QWidget; auto *left = new QVBoxLayout(leftColumn); left->setContentsMargins(0, 0, 0, 0); left->setSpacing(atlas::px("s3"));
    leftColumn->setMaximumWidth(kPrimaryWidth); leftColumn->setMinimumWidth(300); layout->addWidget(leftColumn, 1);
    auto *library = new kit::Pane(t("Disc library", "Biblioteca de discos")); library->setObjectName("atlasLibrary"); left->addWidget(library, 1);
    auto *libraryBody = new QVBoxLayout(library->body()); libraryBody->setContentsMargins(0, 0, 0, 0); libraryBody->setSpacing(atlas::px("s2"));
    auto *discTable = new RowTable(0, 3); discTable->setHorizontalHeaderLabels({"Disc", "Kind", "Path"}); discTable->placeholder = t("No discs yet. Use Add disc to choose your Melee disc image.", "No discs yet. Use Add disc to choose your Melee disc image.");
    discs_ = discTable; discs_->setObjectName("atlasDiscs");
    discs_->setSelectionBehavior(QAbstractItemView::SelectRows); discs_->setSelectionMode(QAbstractItemView::SingleSelection);
    discs_->setEditTriggers(QAbstractItemView::NoEditTriggers); discs_->verticalHeader()->hide(); discs_->horizontalHeader()->hide();
    discs_->setItemDelegate(new kit::RowDelegate(discs_)); discs_->setColumnHidden(1, true); discs_->setColumnHidden(2, true);
    discs_->horizontalHeader()->setSectionResizeMode(0, QHeaderView::Stretch); discs_->setShowGrid(false); discs_->setAlternatingRowColors(false);
    discs_->setFrameShape(QFrame::NoFrame); discs_->setVerticalScrollMode(QAbstractItemView::ScrollPerPixel); discs_->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    discs_->setMinimumHeight(kit::RowDelegate::rowHeight() + 4);
    libraryBody->addWidget(discs_, 1);
    auto *actions = new QHBoxLayout; actions->setSpacing(atlas::px("s2")); libraryBody->addLayout(actions);
    auto *add = button(actions, t("+ ADD DISC", "+ AÑADIR"), [this] { addDisc(); }); add->setObjectName("atlasAddDisc");
    auto *manage = new kit::Button(t("MANAGE…", "GESTIONAR…")); manage->setObjectName("atlasManage"); actions->addWidget(manage); actions->addStretch();
    auto *menu = new QMenu(manage);
    auto menuAction = [&](const QString &title, const std::function<void()> &fn) { auto *a = menu->addAction(title); connect(a, &QAction::triggered, this, [this, fn] { guarded(fn); }); };
    menuAction(t("Change ISO…", "Cambiar ISO…"), [this] {
        int i = selectedDisc(); if (i < 0) return;
        auto path = QFileDialog::getOpenFileName(this, t("Change ISO", "Cambiar ISO"), {}, "Disc images (*.iso *.gcm);;All files (*)"); if (path.isEmpty()) return;
        auto info = probeDisc(path);
        if (info.verdict == DiscInfo::Bad) throw std::runtime_error(info.message.toUtf8().constData());
        if (info.verdict == DiscInfo::Warn && QMessageBox::warning(this, t("Modified disc", "Disco modificado"), info.message, QMessageBox::Ok | QMessageBox::Cancel) != QMessageBox::Ok) return;
        auto &d = settings_.discs[i]; d.path = path; d.kind = info.kind; save(); refreshDiscs(d.id);
    });
    menuAction(t("Rename…", "Renombrar…"), [this] {
        int i = selectedDisc(); if (i < 0) return; bool ok;
        auto name = QInputDialog::getText(this, t("Rename disc", "Renombrar disco"), t("Name", "Nombre"), QLineEdit::Normal, settings_.discs[i].name, &ok).trimmed();
        if (ok && !name.isEmpty()) { settings_.discs[i].name = name; save(); refreshDiscs(settings_.discs[i].id); }
    });
    menuAction(t("Make default", "Usar por defecto"), [this] { int i = selectedDisc(); if (i >= 0) { settings_.defaultId = settings_.discs[i].id; save(); refreshDiscs(settings_.defaultId); } });
    menuAction(t("Open saves", "Abrir partidas guardadas"), [this] { int i = selectedDisc(); if (i >= 0) { auto p = userDir_ + "/saves/" + settings_.discs[i].id; QDir().mkpath(p); openPath(p); } });
    menu->addSeparator();
    menuAction(t("Forget disc…", "Olvidar disco…"), [this] {
        int i = selectedDisc(); if (i < 0) return;
        if (QMessageBox::question(this, t("Forget disc?", "¿Olvidar disco?"), t("Remove this disc from the list? Its ISO and saves will be kept.", "¿Quitar este disco de la lista? Se conservan la ISO y las partidas guardadas.")) != QMessageBox::Yes) return;
        settings_.discs.removeAt(i); if (settings_.defaultIndex() >= 0) settings_.defaultId = settings_.discs[settings_.defaultIndex()].id; else settings_.defaultId.clear(); save(); refreshDiscs();
    });
    connect(manage, &QPushButton::clicked, this, [manage, menu] { menu->exec(manage->mapToGlobal(QPoint(0, manage->height()))); });
    // Options: the three switches and the volume, each a row
    auto *options = new kit::Pane(t("Options", "Opciones")); left->addWidget(options);
    auto *optionList = new QVBoxLayout(options->body()); optionList->setContentsMargins(0, 0, 0, 0); optionList->setSpacing(atlas::px("s1") - 1);
    for (const auto &item : QList<QPair<QString, QString>>{{"unlock_all", t("Unlock everything", "Desbloquear todo")}, {"skip_intro", t("Skip intro", "Saltar introducción")}, {"close_on_play", t("Close launcher on play", "Cerrar lanzador al jugar")}}) {
        auto *check = new kit::Toggle; check->setObjectName("opt_" + item.first); check->setAccessibleName(item.second); check->setChecked(settings_.flag(item.first, item.first != "close_on_play"));
        optionList->addWidget(new OptionRow(item.second, check, check, true));
        connect(check, &QAbstractButton::toggled, this, [this, key = item.first](bool on) { guarded([&] { settings_.options[key] = on ? "1" : "0"; save(); }); });
    }
    auto *volume = new QSlider(Qt::Horizontal); volume->setObjectName("atlasVolume"); volume->setAccessibleName(t("VOLUME", "VOLUMEN")); volume->setRange(0, 100); volume->setValue(settings_.option("volume", "50").toInt()); volume->setMinimumWidth(120);
    auto *amount = capLabel(QString::number(volume->value()) + "%", atlas::Role::Body14, "text2"); amount->setFixedWidth(42); amount->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
    auto *volumeControl = new QWidget; auto *volumeLayout = new QHBoxLayout(volumeControl); volumeLayout->setContentsMargins(0, 0, 0, 0); volumeLayout->setSpacing(atlas::px("s2")); volumeLayout->addWidget(volume, 1); volumeLayout->addWidget(amount);
    optionList->addWidget(new OptionRow(t("VOLUME", "VOLUMEN"), volumeControl, volume, false));
    connect(volume, &QSlider::valueChanged, this, [this, amount](int value) { amount->setText(QString::number(value) + "%"); guarded([&] { settings_.options["volume"] = QString::number(value); save(); }); });
    // explainer (right, fills, at least 240): what is selected, then the Play block
    auto *rightColumn = new QWidget; auto *right = new QVBoxLayout(rightColumn); right->setContentsMargins(0, 0, 0, 0); right->setSpacing(atlas::px("s3"));
    rightColumn->setMinimumWidth(kExplainerMin); layout->addWidget(rightColumn, 1);
    auto *explainer = new ExplainerPane(t("Play with", "Play with")); right->addWidget(explainer, 1);
    discTitle_ = explainer->title(); discDetails_ = explainer->what();
    modsOnLabel_ = explainer->addFact(t("Mods", "Mods"), "-");
    explainer->addFact(t("Build", "Build"), versionText(appDir_));
    auto *more = new kit::Button(t("Mods for this disc", "Mods for this disc")); more->setObjectName("atlasMore"); more->setKitIcon("right"); explainer->more()->addWidget(more, 0, Qt::AlignLeft);
    connect(more, &QPushButton::clicked, this, [this] { selectMods(); });
    auto *go = new QVBoxLayout; go->setSpacing(atlas::px("s2")); right->addLayout(go);
    auto *note = new NoteLine; playNote_ = note; go->addWidget(note);
    auto *play = new kit::Button(t("PLAY", "JUGAR")); play->setObjectName("atlasPlay"); play->setPrimary(true); play->setKitIcon("right"); play->setMinimumHeight(54); play->setDefault(true); go->addWidget(play); play_ = play;
    connect(play_, &QPushButton::clicked, this, [this] { this->play(); });
    connect(discs_, &QTableWidget::itemSelectionChanged, this, [this] { showSelectedDisc(); });
    connect(discs_, &QTableWidget::cellDoubleClicked, this, [this] { this->play(); });
    connect(discs_, &QTableWidget::activated, this, [this] { this->play(); });                  // Enter on a row plays, as double-click does
    setTabOrder(play_, discs_);
    return page;
}
void Window::addDisc(const QString &given) { guarded([&] {
    auto path = given.isEmpty() ? QFileDialog::getOpenFileName(this, t("Add disc", "Añadir disco"), {}, "Disc images (*.iso *.gcm);;All files (*)") : given;
    if (path.isEmpty()) return; path = QFileInfo(path).absoluteFilePath();
    for (const auto &d : settings_.discs) if (QFileInfo(d.path).canonicalFilePath() == QFileInfo(path).canonicalFilePath()) { refreshDiscs(d.id); return; }
    auto info = probeDisc(path);
    if (info.verdict == DiscInfo::Bad) throw std::runtime_error(info.message.toUtf8().constData());
    if (info.verdict == DiscInfo::Warn && QMessageBox::warning(this, t("Modified disc", "Disco modificado"), info.message, QMessageBox::Ok | QMessageBox::Cancel) != QMessageBox::Ok) return;
    Disc d{settings_.newId(info.kind), info.kind, info.kind, path}; settings_.discs.append(d); settings_.defaultId = d.id; save(); refreshDiscs(d.id);
}); }
void Window::play() { guarded([&] {
    if (process_.state() != QProcess::NotRunning) return;
#ifdef Q_OS_LINUX
    if (graphicsBusy_) return;
#endif
    int i = selectedDisc(); if (i < 0) { addDisc(); return; }
    LaunchSpec spec;
    try { spec = prepareLaunch(appDir_, userDir_, settings_, settings_.discs[i]); }
    catch (const std::exception &e) {
        diag_ = {}; diag_.prepareError = QString::fromUtf8(e.what()); runDir_.clear();
        auto ctx = diagContext(true); ctx.finished = true; ctx.discPaths << settings_.discs[i].path;
        showLaunchFailure(writeDiagnostics(ctx)); return;
    }
    save();
#ifdef Q_OS_LINUX
    pendingLaunch_ = spec; checkGraphics(true);
#else
    startGame(spec);
#endif
}); }
void Window::startGame(const LaunchSpec &spec) {
    runDir_ = spec.workingDirectory;
    settings_.options["last_run"] = runDir_; save();
    process_.setProgram(spec.program); process_.setArguments(spec.arguments); process_.setWorkingDirectory(spec.workingDirectory); process_.setProcessEnvironment(spec.environment);
    launcher::captureRedacted(process_, spec.logFile, launcher::redactorForLaunch(spec.arguments));
    play_->setEnabled(false); play_->setToolTip(t("Game running.", "Game running.")); statusBar()->showMessage(t("Game running. Logs: ", "Juego en ejecución. Registros: ") + runDir_);
    diag_ = {}; diag_.spec = spec; diag_.haveSpec = true; diag_.stamp = QDateTime::currentDateTime().toString("yyyyMMdd-HHmmss");
    auto &sp = diag_.spawn; sp.attempted = true; sp.program = spec.program; sp.arguments = spec.arguments; sp.workingDirectory = spec.workingDirectory; sp.stdoutFile = spec.logFile;
    launchClock_.start();
    process_.start();
    // A report exists from the moment the game starts, so a hang or a killed launcher still leaves one.
    if (sp.started) { auto ctx = diagContext(false); writeDiagnostics(ctx); }
    if (settings_.flag("close_on_play")) hide();
}
#ifdef Q_OS_LINUX
void Window::checkGraphics(bool forLaunch) { guarded([&] {
    if (graphicsBusy_ || process_.state() != QProcess::NotRunning) return;
    auto env = forLaunch ? pendingLaunch_.environment : QProcessEnvironment::systemEnvironment();
    // A launch environment is already the game's own; otherwise build it the same way prepareLaunch does.
    if (!forLaunch) applyGameLibraryEnvironment(env, appDir_);
    graphicsBusy_ = true; graphicsForLaunch_ = forLaunch; graphicsTimedOut_ = false;
    graphicsOutput_.clear(); graphicsErrors_.clear(); play_->setEnabled(false); play_->setToolTip(t("Checking graphics...", "Comprobando gráficos...")); graphicsDevice_->setEnabled(false);
    graphicsDetails_->setPlainText(t("Checking 32-bit Vulkan drivers...", "Comprobando los controladores Vulkan de 32 bits..."));
    statusBar()->showMessage(t("Checking graphics...", "Comprobando gráficos..."));
    graphicsProcess_.setProgram(appDir_ + "/bin/melee-graphics-probe");
    graphicsProcess_.setWorkingDirectory(appDir_); graphicsProcess_.setProcessEnvironment(env);
    graphicsProcess_.start(); graphicsTimeout_->start(15000);
}); }
void Window::finishGraphics(int code) {
    if (!graphicsBusy_) return;
    graphicsTimeout_->stop(); graphicsBusy_ = false; play_->setEnabled(true); updatePlayState(); graphicsDevice_->setEnabled(true);
    guarded([&] {
        auto report = parseGraphicsReport(graphicsOutput_, code);
        if (graphicsTimedOut_) report.error = "The 32-bit graphics check timed out.";
        else if (code == -1) report.error = "The 32-bit graphics helper could not run or crashed. " + QString::fromUtf8(graphicsErrors_).left(2048);
        const auto selection = settings_.option("graphics_device", "auto");
        bool selected = report.matchesSelection(selection);
        QString text = report.summary();
        if (graphicsForLaunch_ && report.ready() && !selected) text += "\nThe installed device-selection controls did not isolate the selected GPU. Choose Automatic or update the driver's selection layer.";
        if (!report.ready() || (graphicsForLaunch_ && !selected)) text += "\n\n" + graphicsDriverHelp(osRelease());
        graphicsDetails_->setPlainText(text);
        auto log = graphicsForLaunch_ ? pendingLaunch_.workingDirectory + "/graphics-preflight.log" : userDir_ + "/graphics-preflight.log";
        writeAtomic(log, (text + "\n\nSelected GPU: " + selection + "\nOS:\n" + osRelease() + "\nProbe stdout:\n" + QString::fromUtf8(graphicsOutput_) + "\nProbe stderr:\n" + QString::fromUtf8(graphicsErrors_)).toUtf8());
        if (!graphicsForLaunch_) {
            graphicsDevice_->blockSignals(true); graphicsDevice_->clear();
            graphicsDevice_->addItem(t("Automatic", "Automático"), "auto");
            for (const auto &d : report.devices) if (d.usable && (d.vendor == 0x1002 || d.vendor == 0x8086 || d.vendor == 0x10de) && graphicsDevice_->findData(d.selector()) < 0) graphicsDevice_->addItem(d.name + " (" + d.selector() + ")", d.selector());
            if (graphicsDevice_->findData(selection) < 0) graphicsDevice_->addItem(selection + t(" (saved; unavailable)", " (guardada; no disponible)"), selection);
            graphicsDevice_->setCurrentIndex(graphicsDevice_->findData(selection)); graphicsDevice_->blockSignals(false);
            statusBar()->showMessage(report.ready() ? t("32-bit Vulkan check passed.", "Comprobación de Vulkan de 32 bits correcta.") : t("Graphics check needs attention. See Diagnostics.", "La comprobación requiere atención. Consulta Diagnóstico."));
            return;
        }
        if (!selected) {
            QMessageBox dialog(QMessageBox::Warning, t("Graphics check", "Comprobación de gráficos"), text, QMessageBox::Cancel, this);
            dialog.setTextFormat(Qt::PlainText); dialog.setDetailedText("Preflight log: " + log);
            auto *attempt = dialog.addButton(t("Try game anyway", "Intentar iniciar de todos modos"), QMessageBox::AcceptRole);
            dialog.exec(); if (dialog.clickedButton() != attempt) return;
        }
        startGame(pendingLaunch_);
    });
}
#endif
void Window::refreshMods() {
    auto entries = installedMods(modsDir(appDir_, userDir_)); filling_ = true;
    const int keep = mods_->currentRow();
    mods_->setRowCount(entries.size());
    for (int row = 0; row < entries.size(); ++row) {
        const auto &m = entries[row]; auto *check = new QTableWidgetItem(m.id); check->setCheckState(m.enabled ? Qt::Checked : Qt::Unchecked);
        QVariantMap details{{"name", m.name}, {"version", m.version}, {"description", m.description}, {"requires", m.requires.join(", ")}, {"conflicts", m.conflicts.join(", ")}};
        check->setData(kDetailsRole, details);
        check->setData(kit::TitleRole, m.name.isEmpty() ? m.id : m.name);
        check->setData(kit::SubRole, m.id + (m.version.isEmpty() ? QString() : "  v" + m.version));
        mods_->setItem(row, 0, check); mods_->setItem(row, 1, new QTableWidgetItem(m.name)); mods_->setItem(row, 2, new QTableWidgetItem(m.version));
        mods_->setRowHeight(row, kit::RowDelegate::rowHeight());
    }
    filling_ = false;
    if (entries.size() > 0) mods_->selectRow(keep >= 0 ? std::min<int>(keep, entries.size() - 1) : 0);   // the explainer always has a mod to show
    if (auto *pane = findChild<kit::Pane *>("atlasInstalled")) pane->setCount(QString::number(entries.size()));
    if (modsOnLabel_) { int on = 0; for (const auto &m : entries) on += m.enabled; modsOnLabel_->setText(QString::number(on) + " " + t("on", "on")); }
    showSelectedMod();
}
// The explainer of the Mods tab follows the selected row: its sentence, its version and what it needs.
void Window::showSelectedMod() {
    auto *item = mods_->item(mods_->currentRow(), 0);
    if (!item) {
        modTitle_->setText(t("No mod selected", "No mod selected"));
        modDetails_->setText(t("Place each local mod in its own folder inside Mods. Changes take effect at the next game launch.", "Coloca cada mod local en su propia carpeta dentro de Mods. Los cambios se aplican al volver a iniciar el juego."));
        modVersion_->setText("-"); modRequires_->setText("-"); modConflicts_->setText("-");
        return;
    }
    const auto d = item->data(kDetailsRole).toMap();
    modTitle_->setText(item->data(kit::TitleRole).toString().toUpper());
    modDetails_->setText(d["description"].toString().isEmpty() ? t("No description.", "No description.") : d["description"].toString());
    auto orDash = [](const QString &s) { return s.isEmpty() ? QString("-") : s; };
    modVersion_->setText(orDash(d["version"].toString())); modRequires_->setText(orDash(d["requires"].toString())); modConflicts_->setText(orDash(d["conflicts"].toString()));
    for (auto *l : {modVersion_, modRequires_, modConflicts_}) l->setToolTip(l->text());
}
QWidget *Window::modsTab() {
    auto *page = new QWidget; auto *layout = new QHBoxLayout(page); layout->setContentsMargins(0, 0, 0, 0); layout->setSpacing(atlas::px("s3"));
    auto *leftColumn = new QWidget; auto *left = new QVBoxLayout(leftColumn); left->setContentsMargins(0, 0, 0, 0); left->setSpacing(atlas::px("s3"));
    leftColumn->setMaximumWidth(kPrimaryWidth); leftColumn->setMinimumWidth(300); layout->addWidget(leftColumn, 1);
    auto *installed = new kit::Pane(t("Installed mods", "Mods instalados")); installed->setObjectName("atlasInstalled"); left->addWidget(installed, 1);
    auto *body = new QVBoxLayout(installed->body()); body->setContentsMargins(0, 0, 0, 0); body->setSpacing(atlas::px("s2"));
    body->addWidget(paragraph(t("Place each local mod in its own folder inside Mods. Changes take effect at the next game launch.", "Coloca cada mod local en su propia carpeta dentro de Mods. Los cambios se aplican al volver a iniciar el juego."), atlas::Role::Body12, "muted"));
    auto *modTable = new RowTable(0, 3); modTable->setHorizontalHeaderLabels({t("Enabled / ID", "Activado / ID"), t("Name", "Nombre"), t("Version", "Versión")});
    modTable->placeholder = t("No mods installed. Open the mods folder to add one.", "No mods installed. Open the mods folder to add one.");
    mods_ = modTable; mods_->setObjectName("atlasMods");
    mods_->setSelectionBehavior(QAbstractItemView::SelectRows); mods_->setSelectionMode(QAbstractItemView::SingleSelection);
    mods_->setEditTriggers(QAbstractItemView::NoEditTriggers); mods_->verticalHeader()->hide(); mods_->horizontalHeader()->hide();
    mods_->setItemDelegate(new kit::RowDelegate(mods_)); mods_->setColumnHidden(1, true); mods_->setColumnHidden(2, true);
    mods_->horizontalHeader()->setSectionResizeMode(0, QHeaderView::Stretch); mods_->setShowGrid(false); mods_->setAlternatingRowColors(false);
    mods_->setFrameShape(QFrame::NoFrame); mods_->setVerticalScrollMode(QAbstractItemView::ScrollPerPixel); mods_->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    mods_->setMinimumHeight(kit::RowDelegate::rowHeight() + 4);
    body->addWidget(mods_, 1);
    auto *grid = new QGridLayout; grid->setSpacing(atlas::px("s2")); body->addLayout(grid); int n = 0;
    auto action = [&](const QString &text, const std::function<void()> &fn) { auto *b = new kit::Button(text); grid->addWidget(b, n / 2, n % 2); ++n; connect(b, &QPushButton::clicked, b, fn); return b; };
    action(t("Open mods folder", "Abrir carpeta de mods"), [this] { auto p = modsDir(appDir_, userDir_); QDir().mkpath(p); openPath(p); });
    action(t("Open scripts folder", "Abrir carpeta de scripts"), [this] { auto p = QDir(appDir_ + "/scripts").exists() ? appDir_ + "/scripts" : userDir_ + "/scripts"; QDir().mkpath(p); openPath(p); });
    action(t("Refresh", "Actualizar"), [this] { guarded([&] { refreshMods(); }); });
    action(t("Remove…", "Quitar…"), [this] { guarded([&] {
        auto *item = mods_->item(mods_->currentRow(), 0); if (!item) return;
        if (QMessageBox::question(this, t("Remove mod?", "¿Quitar mod?"), t("Move this mod into Mods/.removed? You can restore it from that folder.", "¿Mover este mod a Mods/.removed? Puedes restaurarlo desde esa carpeta.")) != QMessageBox::Yes) return;
        removeMod(modsDir(appDir_, userDir_), item->text()); refreshMods();
    }); });
    connect(mods_, &QTableWidget::itemChanged, this, [this](QTableWidgetItem *item) { if (!filling_ && item->column() == 0) {
        guarded([&] { setModEnabled(modsDir(appDir_, userDir_), item->text(), item->checkState() == Qt::Checked); }); guarded([&] { refreshMods(); });
    } });
    connect(mods_, &QTableWidget::itemSelectionChanged, this, [this] { showSelectedMod(); });
    auto *explainer = new ExplainerPane(t("Mod", "Mod")); explainer->setMinimumWidth(kExplainerMin); layout->addWidget(explainer, 1);
    modTitle_ = explainer->title(); modDetails_ = explainer->what();
    modVersion_ = explainer->addFact(t("Version", "Versión"), "-"); modRequires_ = explainer->addFact(t("Requires", "Requiere"), "-"); modConflicts_ = explainer->addFact(t("Conflicts", "Conflictos"), "-");
    return page;
}
QWidget *Window::diagnosticsTab() {
    auto *page = new QWidget; auto *layout = new QHBoxLayout(page); layout->setContentsMargins(0, 0, 0, 0); layout->setSpacing(atlas::px("s3"));
    // primary: scrolls, so nothing is clipped at 900 x 600 or at 150 percent
    auto *scroll = new QScrollArea; scroll->setObjectName("atlasDiagnostics"); scroll->setWidgetResizable(true); scroll->setFrameShape(QFrame::NoFrame);
    scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff); scroll->setMaximumWidth(kPrimaryWidth + 14); scroll->setMinimumWidth(300);
    auto *content = new QWidget; auto *layout2 = new QVBoxLayout(content); layout2->setContentsMargins(0, 0, atlas::px("s2") + 6, 0); layout2->setSpacing(atlas::px("s3")); scroll->setWidget(content);
    layout->addWidget(scroll, 1);
    auto bodyOf = [&](const QString &heading) { auto *pane = new kit::Pane(heading); layout2->addWidget(pane); auto *v = new QVBoxLayout(pane->body()); v->setContentsMargins(0, 0, 0, 0); v->setSpacing(atlas::px("s2")); return v; };
    auto toggleRow = [&](QBoxLayout *into, const QString &title, const QString &name, bool initial, const std::function<void(bool)> &apply) {
        auto *w = new kit::Toggle; w->setObjectName(name); w->setAccessibleName(title); w->setChecked(initial); into->addWidget(new OptionRow(title, w, w, true));
        connect(w, &QAbstractButton::toggled, this, [this, apply](bool v) { guarded([&] { apply(v); }); }); return w;
    };
#ifdef Q_OS_LINUX
    auto *graphicsLayout = bodyOf(t("Linux graphics", "Gráficos de Linux"));
    graphicsDevice_ = rowCombo(graphicsLayout, t("Game GPU", "GPU del juego"));
    graphicsDevice_->addItem(t("Automatic", "Automático"), "auto");
    auto savedGpu = settings_.option("graphics_device", "auto");
    if (savedGpu != "auto") { graphicsDevice_->addItem(savedGpu + t(" (saved; check graphics)", " (guardada; comprobar gráficos)"), savedGpu); graphicsDevice_->setCurrentIndex(1); }
    connect(graphicsDevice_, qOverload<int>(&QComboBox::currentIndexChanged), this, [this] { guarded([&] { settings_.options["graphics_device"] = graphicsDevice_->currentData().toString(); save(); }); });
    graphicsDetails_ = new QPlainTextEdit; graphicsDetails_->setReadOnly(true); graphicsDetails_->setMinimumHeight(120); graphicsDetails_->setMaximumHeight(180);
    graphicsDetails_->setPlainText(t("Check graphics to list GPUs available to the 32-bit game. Play checks the selected GPU before starting.", "Comprueba los gráficos para ver las GPU disponibles para el juego de 32 bits. Jugar comprueba la GPU seleccionada antes de iniciar.")); graphicsLayout->addWidget(graphicsDetails_);
    auto *graphicsRow = new QHBoxLayout; graphicsLayout->addLayout(graphicsRow);
    button(graphicsRow, t("Check graphics", "Comprobar gráficos"), [this] { checkGraphics(false); });
    button(graphicsRow, t("Driver help", "Ayuda de controladores"), [this] {
        QMessageBox dialog(QMessageBox::Information, t("32-bit graphics drivers", "Controladores gráficos de 32 bits"), graphicsDriverHelp(osRelease()), QMessageBox::Ok, this); dialog.setTextFormat(Qt::PlainText); dialog.exec();
    });
    graphicsRow->addStretch();
#endif
    auto *logging = bodyOf(t("Logging", "Logging"));
    for (const auto &entry : QList<std::tuple<QString, QString, bool>>{{t("Log everything (large logs)", "Registrar todo (registros grandes)"), "log_all", false}, {t("Log scene changes", "Registrar cambios de escena"), "log_scene", true}})
        toggleRow(logging, std::get<0>(entry), "diag_" + std::get<1>(entry), settings_.flag(std::get<1>(entry), std::get<2>(entry)), [this, key = std::get<1>(entry)](bool v) { settings_.options[key] = v ? "1" : "0"; save(); });
    auto combo = [&](const QString &title, const QString &key, const QStringList &choices, int offset, int fallback) {
        auto *w = rowCombo(logging, title); w->setObjectName("diag_" + key); w->addItems(choices); w->setCurrentIndex(std::clamp(settings_.option(key, QString::number(fallback)).toInt() - offset, 0, int(choices.size()) - 1));
        connect(w, qOverload<int>(&QComboBox::currentIndexChanged), this, [this, key, offset](int v) { guarded([&] { settings_.options[key] = QString::number(v + offset); save(); }); });
    };
    combo(t("Render diagnostics", "Diagnóstico gráfico"), "log_render", {t("Off", "Desactivado"), t("Once per scene", "Una vez por escena"), t("Every block", "Cada bloque")}, -1, 0);
    combo(t("Controller diagnostics", "Diagnóstico de mandos"), "pad_diag", {t("Game default", "Por defecto"), "0", "1", "2"}, -1, -1);
    combo(t("Release adapter on focus loss", "Liberar adaptador al perder el foco"), "pad_release_on_blur", {t("Game default", "Por defecto"), t("Off", "Desactivado"), t("On", "Activado")}, -1, -1);
    const QList<QPair<QString, QString>> categories = {{"watchdog", t("Watchdog samples", "Muestras de ejecución")}, {"mex", t("m-ex internals", "Internos de m-ex")}, {"heap", t("Memory allocations", "Asignaciones de memoria")}, {"dvd", t("Disc file trace", "Accesos a archivos del disco")}, {"tex", t("UI texture loads", "Carga de texturas de la interfaz")}, {"frontend", t("Menu layouts", "Diseños de menús")}, {"audio", t("Sound bank loads", "Carga de bancos de sonido")}};
    const QList<QPair<QString, QString>> traces = {{"gr", t("Stage code trace", "Traza del código de escenarios")}, {"mexcalls", t("m-ex engine calls", "Llamadas de m-ex al motor")}, {"card", t("Memory card diagnostics", "Diagnóstico de tarjetas de memoria")}, {"profile", t("Frame timing", "Tiempos de fotogramas")}, {"fps", t("Show frame rate", "Mostrar fotogramas por segundo")}, {"aurora", t("Renderer log", "Registro gráfico")}, {"osreport", t("Report format trace", "Traza de formatos de informes")}};
    for (const auto &group : {qMakePair(QString("log_categories"), categories), qMakePair(QString("traces"), traces)}) {
        auto *list = bodyOf(group.first == "traces" ? t("Traces", "Trazas") : t("Log categories", "Categorías del registro"));
        for (const auto &entry : group.second)
            toggleRow(list, entry.second, group.first + "_" + entry.first, settings_.option(group.first).split(',').contains(entry.first), [this, key = group.first, value = entry.first](bool on) {
                auto items = settings_.option(key).split(',', Qt::SkipEmptyParts); items.removeAll(value); if (on) items << value; settings_.options[key] = items.join(','); save(); });
    }
    auto *reports = bodyOf(t("Reports", "Informes"));
    auto *grid = new QGridLayout; grid->setSpacing(atlas::px("s2")); reports->addLayout(grid); int n = 0;      // one column: these labels are long
    auto lastRun = [this] { return runDir_.isEmpty() ? settings_.option("last_run", userDir_ + "/runs") : runDir_; };
    auto action = [&](const QString &text, const std::function<void()> &fn) { auto *b = new kit::Button(text); grid->addWidget(b, n, 0); ++n; connect(b, &QPushButton::clicked, b, fn); return b; };
    action(t("Open log folder", "Abrir carpeta de registros"), [this, lastRun] { openPath(lastRun()); });
    action(t("Open game log", "Abrir registro del juego"), [this, lastRun] { openPath(lastRun() + "/melee-pc.log"); });
    action(t("Copy launch diagnostics", "Copy launch diagnostics"), [this] { copyDiagnostics(); });
    action(t("Run diagnostics without launching", "Run diagnostics without launching"), [this] { runDiagnosticsOnly(); });
    action(t("Copy latest crash report", "Copiar último informe de fallo"), [this, lastRun] { guarded([&] {
        auto report = latestCrash(lastRun()); if (report.isEmpty()) { statusBar()->showMessage(t("No crash report in the last session.", "No hay informe de fallo en la última sesión.")); return; }
        QApplication::clipboard()->setText(readText(report, 64 * 1024)); statusBar()->showMessage(t("Crash report copied.", "Informe de fallo copiado."));
    }); });
    layout2->addStretch();
    // explainer
    auto *explainer = new ExplainerPane(t("Diagnostics", "Diagnóstico")); explainer->setMinimumWidth(kExplainerMin); layout->addWidget(explainer, 1);
    explainer->title()->setText(t("FIND OUT WHY", "FIND OUT WHY"));
    explainer->what()->setText(t("A report is written for every launch attempt. Copy it and send it when asking for help.", "A report is written for every launch attempt. Copy it and send it when asking for help."));
    auto *where = explainer->addFact(t("Reports", "Informes"), QDir::toNativeSeparators(diagnosticsDir(userDir_))); where->setToolTip(where->text());
    return page;
}
QWidget *Window::aboutTab() {
    auto *page = new QWidget; auto *layout = new QHBoxLayout(page); layout->setContentsMargins(0, 0, 0, 0); layout->setSpacing(atlas::px("s3"));
    QString version = t("development build", "versión de desarrollo");
    try { version = readText(appDir_ + "/version.txt", 16384).section('\n', 0, 0); } catch (...) {}
    auto *leftColumn = new QWidget; auto *left = new QVBoxLayout(leftColumn); left->setContentsMargins(0, 0, 0, 0); left->setSpacing(atlas::px("s3"));
    leftColumn->setMaximumWidth(kPrimaryWidth); leftColumn->setMinimumWidth(300); layout->addWidget(leftColumn, 1);
    auto *about = new kit::Pane(t("This launcher", "This launcher")); left->addWidget(about);
    auto *body = new QVBoxLayout(about->body()); body->setContentsMargins(0, 0, 0, 0); body->setSpacing(atlas::px("s2"));
    body->addWidget(paragraph(t("Bring your own disc image. Game data is never bundled with the launcher.", "Usa tu propia imagen de disco. El lanzador no incluye datos del juego.")));
    for (const auto &entry : QList<QPair<QString, QString>>{{t("Game folder: ", "Carpeta del juego: "), appDir_}, {t("User data: ", "Datos del usuario: "), userDir_}}) {
        auto *line = new ElidedLabel(entry.first + QDir::toNativeSeparators(entry.second), atlas::Role::Body14, "text2"); line->setToolTip(entry.second); body->addWidget(line);
    }
    auto *lang = rowCombo(body, t("Language (next launch)", "Idioma (al reiniciar)")); lang->setObjectName("atlasLanguage");
    lang->addItem(t("System language", "Idioma del sistema"), "auto"); lang->addItem("English", "en"); lang->addItem("Español", "es");
    lang->setCurrentIndex(std::max(0, lang->findData(settings_.option("language", "auto"))));
    connect(lang, qOverload<int>(&QComboBox::currentIndexChanged), this, [this, lang] { guarded([&] { settings_.options["language"] = lang->currentData().toString(); save(); }); });
    auto *row = new QHBoxLayout; row->setSpacing(atlas::px("s2")); body->addLayout(row);
    button(row, t("Open user data", "Abrir datos del usuario"), [this] { openPath(userDir_); });
    auto *licences = button(row, t("Open licences", "Abrir licencias"), [this] { openPath(QDir(appDir_ + "/LICENSES").exists() ? appDir_ + "/LICENSES" : appDir_ + "/licenses"); }); licences->setObjectName("atlasLicences");
    row->addStretch(); left->addStretch();
    auto *explainer = new ExplainerPane(t("About", "Acerca de")); explainer->setMinimumWidth(kExplainerMin); layout->addWidget(explainer, 1);
    explainer->title()->setText("GD'S MELEE");
    explainer->what()->setText(t("A launcher for the PC port. It starts the game from your own disc and keeps your mods and logs in order.", "A launcher for the PC port. It starts the game from your own disc and keeps your mods and logs in order."));
    explainer->addFact(t("Version", "Versión"), version);
    explainer->addFact("Qt", qVersion());
    auto *type = explainer->addFact(t("Type", "Type"), "Barlow Condensed, Source Sans 3"); type->setToolTip(t("Fonts by Jeremy Tribby (Barlow Condensed) and Adobe (Source Sans 3), both under the SIL Open Font License. The licences are in the Licences folder.", "Fonts by Jeremy Tribby (Barlow Condensed) and Adobe (Source Sans 3), both under the SIL Open Font License. The licences are in the Licences folder."));
    explainer->more()->addWidget(paragraph(t("Fonts: Barlow Condensed (Jeremy Tribby) and Source Sans 3 (Adobe), SIL Open Font License. Qt (The Qt Company) is used under its open-source licences.", "Fonts: Barlow Condensed (Jeremy Tribby) and Source Sans 3 (Adobe), SIL Open Font License. Qt (The Qt Company) is used under its open-source licences."), atlas::Role::Body12, "muted"));
    return page;
}
void Window::selectMods() { rail_->setCurrent(1); }
void Window::screenshots(const QString &dir) {
    QDir().mkpath(dir); show();
    for (int i = 0; i < tabs_->count(); ++i) { rail_->setCurrent(i); QApplication::processEvents(); if (!grab().save(dir + "/launcher-" + QString::number(i) + ".png")) throw std::runtime_error("Cannot save screenshot"); }
}
void Window::closeEvent(QCloseEvent *event) {
    if (process_.state() != QProcess::NotRunning) { quitting_ = true; hide(); event->ignore(); }
    else { event->accept(); QApplication::quit(); }
}
}
