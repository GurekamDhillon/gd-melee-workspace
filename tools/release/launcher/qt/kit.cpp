#include "kit.h"
#include "atlas_icons.h"
#include <QAbstractItemModel>
#include <QKeyEvent>
#include <QMouseEvent>
#include <QPainter>
#include <QStyleOptionViewItem>
#include <QVBoxLayout>
#include <cmath>
#include <QTransform>
#include <algorithm>

// The Atlas parts, painted from the tokens. Flat fills only: no shadows, gradients or antialiasing
// (the icon strokes are the one exception). Every colour and size is an atlas:: value.
namespace launcher::kit {
using atlas::colour;
using atlas::px;

QPainterPath icon(const QString &name) { return icons::path(name); }

static QColor mix(const QColor &a, const QColor &b, qreal t) {
    return QColor(int(a.red() + (b.red() - a.red()) * t + .5), int(a.green() + (b.green() - a.green()) * t + .5),
                  int(a.blue() + (b.blue() - a.blue()) * t + .5), int(a.alpha() + (b.alpha() - a.alpha()) * t + .5));
}
static void flat(QPainter &p) { p.setRenderHint(QPainter::Antialiasing, false); p.setPen(Qt::NoPen); }

void paintIcon(QPainter &p, const QString &name, const QRectF &target, const QColor &c) {
    const QPainterPath path = icon(name);
    if (path.isEmpty()) return;
    p.save();
    p.setRenderHint(QPainter::Antialiasing, true);
    const qreal s = target.width() / 24.0;
    p.translate(target.topLeft()); p.scale(s, s);
    QPen pen(c, 1.6, Qt::SolidLine, Qt::SquareCap, Qt::MiterJoin); p.setPen(pen); p.setBrush(Qt::NoBrush);
    p.drawPath(path);
    p.restore();
}
void paintPlate(QPainter &p, const QRectF &r, const QColor &face, const QColor &edge, qreal edgePx, qreal chamfer) {
    p.setPen(Qt::NoPen);
    p.setBrush(edge); p.drawPolygon(atlas::plate(r, chamfer));
    p.setBrush(face); p.drawPolygon(atlas::plate(r.adjusted(0, 0, 0, -edgePx), chamfer));
}
void paintHatch(QPainter &p, const QPolygonF &area, const QColor &line) {
    p.save(); p.setPen(Qt::NoPen); p.setBrush(QBrush(line, Qt::BDiagPattern)); p.drawPolygon(area); p.restore();   // 8 px: the token "ch"
}

// ---------------------------------------------------------------- Pane
Pane::Pane(const QString &heading, QWidget *parent) : QWidget(parent), heading_(heading) {
    body_ = new QWidget(this);
    auto *l = new QVBoxLayout(this);
    l->setContentsMargins(px("s3"), px("s3") + (heading.isEmpty() ? 0 : 28), px("s3"), px("s3") + px("ch-xs")); l->setSpacing(0);
    l->addWidget(body_, 1);
}
void Pane::setHeading(const QString &text) {
    heading_ = text; auto *l = layout(); l->setContentsMargins(px("s3"), px("s3") + (text.isEmpty() ? 0 : 28), px("s3"), px("s3") + px("ch-xs")); update();
}
void Pane::setCount(const QString &text) { count_ = text; update(); }
void Pane::paintEvent(QPaintEvent *) {
    QPainter p(this); flat(p);
    paintPlate(p, QRectF(rect()), colour("plate"), colour("edge"), px("ch-xs"), px("ch"));
    if (heading_.isEmpty()) return;
    const QFont hf = atlas::font(atlas::Role::Cap14), cf = atlas::font(atlas::Role::Body12);
    QFontMetricsF hm(hf), cm(cf);
    const qreal left = px("s3"), top = px("s3"), h = 20, right = width() - px("s3");
    const qreal countW = count_.isEmpty() ? 0 : cm.horizontalAdvance(count_);
    const qreal room = right - left - (countW ? countW + px("s2") : 0);
    const QString shown = atlas::fit(hm, heading_.toUpper(), room);
    setProperty("headingShown", shown);                                  // a test hook, not a feature
    p.setFont(hf); p.setPen(colour("muted"));
    p.drawText(QRectF(left, top, room, h), Qt::AlignLeft | Qt::AlignVCenter, shown);
    const qreal textW = hm.horizontalAdvance(shown);
    if (countW) { p.setFont(cf); p.setPen(colour("muted")); p.drawText(QRectF(right - countW, top, countW, h), Qt::AlignRight | Qt::AlignVCenter, count_); }
    const qreal ruleL = left + textW + px("s2"), ruleR = right - (countW ? countW + px("s2") : 0);
    if (ruleR > ruleL) p.fillRect(QRectF(ruleL, top + h / 2, ruleR - ruleL, 1), colour("line"));
}

// ---------------------------------------------------------------- Button
Button::Button(const QString &text, QWidget *parent) : QPushButton(text, parent) {
    setCursor(Qt::PointingHandCursor); setFocusPolicy(Qt::StrongFocus); setMouseTracking(true);
    setAutoDefault(true);                                               // Enter presses the focused button (Qt only does this in dialogs by default)
    setFont(atlas::font(atlas::Role::Cap16));
    setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Fixed);
    motion_.setEasingCurve(QEasingCurve::OutCubic);
    connect(&motion_, &QVariantAnimation::valueChanged, this, [this](const QVariant &v) { hover_ = v.toReal(); update(); });
}
static void glide(QVariantAnimation &a, qreal &now, qreal to) {
    a.stop();
    const int d = atlas::motion("m-focus");
    if (d <= 0) { now = to; return; }                                    // reduced motion: a cut
    a.setDuration(d); a.setStartValue(now); a.setEndValue(to); a.start();
}
void Button::enterEvent(QEnterEvent *e) { glide(motion_, hover_, 1.); update(); QPushButton::enterEvent(e); }
void Button::leaveEvent(QEvent *e) { glide(motion_, hover_, 0.); update(); QPushButton::leaveEvent(e); }
QSize Button::sizeHint() const {
    QFontMetricsF fm(atlas::font(role()));
    qreal w = fm.horizontalAdvance(text()) + 2 * px("s4");
    if (!icon_.isEmpty()) w += 18 + px("s2");
    return {int(std::ceil(std::max<qreal>(w, primary_ ? 120 : 64))), primary_ ? 46 : 36};   // 44 / 34 plates plus the 2 px lift
}
void Button::paintEvent(QPaintEvent *) {
    QPainter p(this); flat(p);
    const bool on = isEnabled(), focus = hasFocus() && on, down = isDown() && on;
    const QRectF base(0, 2, width(), height() - 2);
    QRectF r = down ? base.translated(0, 1) : atlas::lifted(base, focus);
    QColor face, edge, fg; qreal edgePx = px("ch-xs");
    if (!on)           { face = colour("plate2"); edge = colour("edge2"); fg = colour("muted"); }
    else if (primary_) { face = down ? colour("ember-d") : mix(colour("ember"), colour("ivory"), hover_ * .12); edge = focus ? colour("ivory") : colour("ember-d"); fg = down ? colour("ivory") : colour("ink"); }
    else               { face = down ? colour("plate") : focus ? colour("lift") : mix(colour("plate2"), colour("lift"), hover_);
                         edge = focus ? colour("ember") : colour("edge2"); fg = focus || hover_ > .5 ? colour("ivory") : colour("text2"); }
    if (down) { edge = colour("ember-d"); edgePx = 1; }
    paintPlate(p, r, face, edge, edgePx, px("ch-s"));
    if (!on) paintHatch(p, atlas::plate(r.adjusted(0, 0, 0, -edgePx), px("ch-s")), colour("line2"));
    // the label: the cap role of the button, one role down when it does not fit, then elided
    const QRectF faceRect = r.adjusted(0, 0, 0, -edgePx);
    qreal x = faceRect.left() + px("s4"), avail = faceRect.width() - 2 * px("s4");
    const bool hasIcon = !icon_.isEmpty();
    if (hasIcon) avail -= 18 + px("s2");
    atlas::Role role_ = role();
    if (QFontMetricsF(atlas::font(role_)).horizontalAdvance(text()) > avail) role_ = primary_ ? atlas::Role::Cap16 : atlas::Role::Cap14;
    const QFont f = atlas::font(role_); QFontMetricsF fm(f);
    const QString shown = atlas::fit(fm, text(), avail);
    const qreal tw = fm.horizontalAdvance(shown), total = tw + (hasIcon ? 18 + px("s2") : 0);
    x = faceRect.left() + (faceRect.width() - total) / 2;
    if (hasIcon) { paintIcon(p, icon_, QRectF(x, faceRect.center().y() - 9, 18, 18), fg); x += 18 + px("s2"); }
    p.setFont(f); p.setPen(fg);
    p.drawText(QRectF(x, faceRect.top(), tw + 2, faceRect.height()), Qt::AlignLeft | Qt::AlignVCenter, shown);
}

// ---------------------------------------------------------------- Toggle
void paintToggle(QPainter &p, const QRectF &box, bool on, bool focus) {
    p.save(); flat(p);
    const QRectF r = atlas::lifted(box, focus);                          // box is the resting plate; 2 px of headroom above it
    const qreal edgePx = focus ? px("ch-xs") : 2;
    const QRectF face = r.adjusted(0, 0, 0, -edgePx);
    paintPlate(p, r, colour("ground"), focus ? colour("ember") : colour("edge"), edgePx, px("ch-xs"));
    const qreal half = face.width() / 2;
    const QRectF offR(face.left(), face.top(), half, face.height()), onR(face.left() + half, face.top(), face.width() - half, face.height());
    QPainterPath clip; clip.addPolygon(atlas::plate(face, px("ch-xs"))); p.setClipPath(clip);
    p.fillRect(on ? onR : offR, on ? colour("jade") : colour("line2"));
    p.setClipping(false);
    p.setFont(atlas::font(atlas::Role::Cap12));
    p.setPen(on ? colour("dim") : colour("ivory")); p.drawText(offR, Qt::AlignCenter, "OFF");
    p.setPen(on ? colour("ink") : colour("dim")); p.drawText(onR, Qt::AlignCenter, "ON");
    p.restore();
}
Toggle::Toggle(QWidget *parent) : QAbstractButton(parent) {
    setCheckable(true); setFocusPolicy(Qt::StrongFocus); setCursor(Qt::PointingHandCursor);
    setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Fixed);
}
void Toggle::paintEvent(QPaintEvent *) {
    QPainter p(this);
    paintToggle(p, QRectF(0, 2, width(), height() - 2), isChecked(), hasFocus());
}

// ---------------------------------------------------------------- Tag
qreal tagWidth(const QString &text) { return QFontMetricsF(atlas::font(atlas::Role::Cap12)).horizontalAdvance(text.toUpper()) + 2 * px("s2"); }
void paintTag(QPainter &p, const QRectF &r, const QString &text, Tag::Tone tone) {
    p.save(); flat(p);
    QColor face = colour("ground"), fg = colour("text2");
    switch (tone) {
    case Tag::Plain: break;
    case Tag::Jade:  face = colour("jade-d"); fg = colour("ivory"); break;
    case Tag::Ember: face = colour("ember"); fg = colour("ink"); break;
    case Tag::Sun:   face = colour("sun").darker(250); fg = colour("sun"); break;
    case Tag::Rose:  face = colour("rose").darker(300); fg = colour("rose").lighter(130); break;
    }
    paintPlate(p, r, face, colour("edge"), 2, px("ch-s"));
    const QFont f = atlas::font(atlas::Role::Cap12); QFontMetricsF fm(f);
    const QString shown = atlas::fit(fm, text.toUpper(), r.width() - 2 * px("s2"));
    p.setFont(f); p.setPen(fg);
    p.drawText(r.adjusted(0, 0, 0, -2), Qt::AlignCenter, shown);
    p.restore();
}
Tag::Tag(const QString &text, Tone tone, QWidget *parent) : QWidget(parent), text_(text), tone_(tone) {
    setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Fixed);
}
QSize Tag::sizeHint() const { return {int(std::min<qreal>(std::ceil(tagWidth(text_)), maximumWidth())), 20}; }
void Tag::paintEvent(QPaintEvent *) { QPainter p(this); paintTag(p, QRectF(rect()), text_, tone_); }

// ---------------------------------------------------------------- KeyChip
KeyChip::KeyChip(const QString &text, QWidget *parent) : QWidget(parent), text_(text) { setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Fixed); }
QSize KeyChip::sizeHint() const {
    return {int(std::ceil(std::max<qreal>(22, QFontMetricsF(atlas::font(atlas::Role::Cap12)).horizontalAdvance(text_.toUpper()) + 2 * px("s2"))) ), 22};
}
void KeyChip::paintEvent(QPaintEvent *) {
    QPainter p(this); flat(p);
    paintPlate(p, QRectF(rect()), colour("text2"), colour("muted"), 2, px("ch-xs"));
    p.setFont(atlas::font(atlas::Role::Cap12)); p.setPen(colour("ink"));
    p.drawText(QRectF(rect()).adjusted(0, 0, 0, -2), Qt::AlignCenter, text_.toUpper());
}

// ---------------------------------------------------------------- TabRail
TabRail::TabRail(const QStringList &names, QWidget *parent) : QWidget(parent), names_(names) {
    setFocusPolicy(Qt::StrongFocus); setAutoFillBackground(false);
    setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Expanding);
}
QRectF TabRail::rowRect(int i) const { return QRectF(px("s3"), 16 + i * 50, width() - 2 * px("s3"), 44); }   // 44 high, 6 apart (the mockup)
void TabRail::setCurrent(int i) {
    if (i < 0 || i >= names_.size() || i == current_) return;
    current_ = i; update(); emit currentChanged(i);
}
void TabRail::keyPressEvent(QKeyEvent *e) {
    const int n = names_.size(); if (!n) return QWidget::keyPressEvent(e);
    int to = current_;
    switch (e->key()) {
    case Qt::Key_Down: to = (current_ + 1) % n; break;
    case Qt::Key_Up: to = (current_ + n - 1) % n; break;
    case Qt::Key_Home: to = 0; break;
    case Qt::Key_End: to = n - 1; break;
    default: return QWidget::keyPressEvent(e);
    }
    setCurrent(to);
}
void TabRail::mousePressEvent(QMouseEvent *e) {
    for (int i = 0; i < names_.size(); ++i) if (rowRect(i).adjusted(0, -3, 0, 3).contains(e->position())) { setFocus(Qt::MouseFocusReason); setCurrent(i); return; }
    QWidget::mousePressEvent(e);
}
void TabRail::paintEvent(QPaintEvent *) {
    QPainter p(this); flat(p);
    p.fillRect(rect(), colour("ground2"));
    for (int i = 0; i < names_.size(); ++i) {
        const bool cur = i == current_, focus = cur && hasFocus();
        const QRectF base = rowRect(i), r = atlas::lifted(base, focus);
        paintPlate(p, r, focus ? colour("lift") : colour("plate2"), focus ? colour("ember") : colour("edge2"), px("ch-xs"), px("ch-s"));
        if (cur) p.fillRect(QRectF(r.right() - 4, r.top(), 4, r.height() - px("ch-xs") - px("ch-s")), colour("jade"));   // selected: jade bar at the right
        if (focus) p.fillRect(atlas::tick(r.adjusted(0, 0, 0, -px("ch-xs"))), colour("ember"));                          // focus: the tick at the left
        const QColor fg = cur ? colour("ivory") : colour("text2");
        const qreal x = r.left() + px("s3") + 4, cy = r.center().y() - px("ch-xs") / 2.0;
        if (i < icons_.size()) paintIcon(p, icons_[i], QRectF(x, cy - 10, 20, 20), cur ? colour("jade") : fg);
        const QFont f = atlas::font(atlas::Role::Cap20); QFontMetricsF fm(f);
        const qreal tx = x + 20 + px("s3");
        p.setFont(f); p.setPen(fg);
        p.drawText(QRectF(tx, r.top(), r.right() - tx - 8, r.height() - px("ch-xs")), Qt::AlignLeft | Qt::AlignVCenter, atlas::fit(fm, names_[i], r.right() - tx - 8));
    }
}

// ---------------------------------------------------------------- RowDelegate
void RowDelegate::paint(QPainter *p, const QStyleOptionViewItem &opt, const QModelIndex &idx) const {
    p->save(); flat(*p);
    const bool selected = opt.state & QStyle::State_Selected, focus = (opt.state & QStyle::State_HasFocus) && opt.widget && opt.widget->hasFocus();
    const bool enabled = opt.state & QStyle::State_Enabled;
    const QRectF base = QRectF(opt.rect).adjusted(0, 2, 0, -3), r = atlas::lifted(base, focus);   // 46 high; the gap and the headroom are in the cell
    const qreal edgePx = px("ch-xs");
    QColor face = selected || focus ? colour("lift") : colour("plate2"), edge = focus ? colour("ember") : colour("edge2");
    paintPlate(*p, r, face, edge, edgePx, px("ch-s"));
    if (!enabled) paintHatch(*p, atlas::plate(r.adjusted(0, 0, 0, -edgePx), px("ch-s")), colour("line"));
    if (selected) p->fillRect(QRectF(r.right() - 4, r.top(), 4, r.height() - edgePx - px("ch-s")), colour("jade"));
    if (focus) p->fillRect(atlas::tick(r.adjusted(0, 0, 0, -edgePx)), colour("ember"));
    const QRectF body = r.adjusted(0, 0, 0, -edgePx);
    qreal x = body.left() + px("s3") + (focus ? 4 : 0), right = body.right() - px("s3") - 4;
    const QString badge = idx.data(BadgeRole).toString();
    if (!badge.isEmpty()) {
        const QRectF b(x, body.center().y() - 16, 32, 32);
        paintPlate(*p, b, colour("ground2"), colour("edge2"), 2, px("ch-xs"));
        paintHatch(*p, atlas::plate(b.adjusted(0, 0, 0, -2), px("ch-xs")), colour("line"));
        p->setFont(atlas::font(atlas::Role::Cap14)); p->setPen(colour("ivory"));
        p->drawText(b.adjusted(0, 0, 0, -2), Qt::AlignCenter, badge);
        x += 32 + px("s3");
    }
    if (idx.data(Qt::CheckStateRole).isValid()) {
        const bool on = idx.data(Qt::CheckStateRole).toInt() == Qt::Checked;
        paintToggle(*p, QRectF(right - 74, body.center().y() - 12, 74, 24), on, false);
        right -= 74 + px("s2");
    }
    const QString tagText = idx.data(TagTextRole).toString();
    if (!tagText.isEmpty()) {
        const qreal w = std::min<qreal>(tagWidth(tagText), std::max<qreal>(0, (right - x) / 2));
        if (w >= 24) { paintTag(*p, QRectF(right - w, body.center().y() - 10, w, 20), tagText, Tag::Tone(idx.data(TagToneRole).isValid() ? idx.data(TagToneRole).toInt() : int(Tag::Jade))); right -= w + px("s2"); }
    }
    QString title = idx.data(TitleRole).toString(); if (title.isEmpty()) title = idx.data(Qt::DisplayRole).toString();
    const QString sub = idx.data(SubRole).toString();
    const QFont tf = atlas::font(atlas::Role::Row16), sf = atlas::font(atlas::Role::Body12);
    QFontMetricsF tm(tf), sm(sf);
    const qreal room = right - x, textH = tm.height() + (sub.isEmpty() ? 0 : sm.height());
    const qreal top = body.center().y() - textH / 2;
    p->setFont(tf); p->setPen(selected || focus ? colour("ivory") : colour("text2"));
    p->drawText(QRectF(x, top, room, tm.height()), Qt::AlignLeft | Qt::AlignVCenter, atlas::fit(tm, title, room));
    if (!sub.isEmpty()) { p->setFont(sf); p->setPen(colour("muted")); p->drawText(QRectF(x, top + tm.height(), room, sm.height()), Qt::AlignLeft | Qt::AlignVCenter, atlas::fit(sm, sub, room)); }
    p->restore();
}
bool RowDelegate::editorEvent(QEvent *e, QAbstractItemModel *model, const QStyleOptionViewItem &opt, const QModelIndex &idx) {
    if (!(idx.flags() & Qt::ItemIsUserCheckable) || !(idx.flags() & Qt::ItemIsEnabled)) return QStyledItemDelegate::editorEvent(e, model, opt, idx);
    if (e->type() == QEvent::MouseButtonRelease || e->type() == QEvent::MouseButtonDblClick) {
        auto *m = static_cast<QMouseEvent *>(e);
        const QRectF base = QRectF(opt.rect).adjusted(0, 2, 0, -3), body = base.adjusted(0, 0, 0, -px("ch-xs"));
        const QRectF hit = QRectF(body.right() - px("s3") - 4 - 74, body.center().y() - 12, 74, 24);
        if (m->button() == Qt::LeftButton && hit.contains(m->position())) {
            if (e->type() == QEvent::MouseButtonRelease) model->setData(idx, idx.data(Qt::CheckStateRole).toInt() == Qt::Checked ? Qt::Unchecked : Qt::Checked, Qt::CheckStateRole);
            return true;
        }
        return false;                                                      // a click elsewhere in the row only selects it
    }
    return QStyledItemDelegate::editorEvent(e, model, opt, idx);          // Space on the row toggles it (Qt's own handling)
}
}
