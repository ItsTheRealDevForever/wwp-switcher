import os
import sys
import ctypes
import keyboard  # Low-level native Windows hotkey hook
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QObject, pyqtProperty, QParallelAnimationGroup, QAbstractAnimation
from PyQt6.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, 
                             QGraphicsPixmapItem, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QWidget)
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QColor, QTransform, QBrush

# Windows Desktop API Configuration
SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02

def set_windows_wallpaper(image_path):
    """Instantly updates the desktop background via Windows API."""
    abs_path = os.path.abspath(image_path)
    ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER, 0, abs_path, 
        SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
    )

class PositionAnimBridge(QObject):
    """Animation bridge to handle horizontal position interpolation during mouse wheel actions."""
    def __init__(self, target_item):
        super().__init__()
        self.target = target_item

    def get_val(self): return self.target.current_progress
    def set_val(self, v):
        self.target.current_progress = v
        self.target.update_visual_state()
    anim_value = pyqtProperty(float, fget=get_val, fset=set_val)


class IntroAnimBridge(QObject):
    """Kinetic intro animation driver interpolating from 0.0 (massive zoom) to 1.0 (rest)."""
    def __init__(self, target_item):
        super().__init__()
        self.target = target_item

    def get_val(self): return self.target.intro_progress
    def set_val(self, v):
        self.target.intro_progress = v
        self.target.update_visual_state()
    anim_value = pyqtProperty(float, fget=get_val, fset=set_val)


class HoverAnimBridge(QObject):
    """Animation bridge handling isolated hover scaling transformations."""
    def __init__(self, target_item):
        super().__init__()
        self.target = target_item

    def get_val(self): return self.target.current_hover_scale
    def set_val(self, v):
        self.target.current_hover_scale = v
        self.target.update_visual_state()
    anim_value = pyqtProperty(float, fget=get_val, fset=set_val)
class WallpaperGraphicsCard(QGraphicsPixmapItem):
    """Cinematic graphic item supporting explosive high-speed zoom breaches and solid layer physics."""
    def __init__(self, file_path, base_pixmap, controller_widget):
        super().__init__(base_pixmap)
        self.file_path = file_path
        self.controller = controller_widget
        
        self.current_progress = 0.0
        self.intro_progress = 0.0        
        self.current_hover_scale = 1.0
        self.is_hovered = False
        
        self.setCacheMode(QGraphicsPixmapItem.CacheMode.DeviceCoordinateCache)
        self.setAcceptHoverEvents(True)
        
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(45)
        self.shadow.setColor(QColor(0, 0, 0, 230))
        self.shadow.setOffset(0, 15)
        self.setGraphicsEffect(self.shadow)
        
        self.pos_bridge = PositionAnimBridge(self)
        self.pos_animation = QPropertyAnimation(self.pos_bridge, b"anim_value")
        self.pos_animation.setDuration(280)
        self.pos_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.hover_bridge = HoverAnimBridge(self)
        self.hover_animation = QPropertyAnimation(self.hover_bridge, b"anim_value")
        self.hover_animation.setDuration(160)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # AGGRESSIVE ZOOM TIMELINE: Rapid 380ms high-speed breach velocity settings
        self.intro_bridge = IntroAnimBridge(self)
        self.intro_animation = QPropertyAnimation(self.intro_bridge, b"anim_value")
        self.intro_animation.setDuration(380) 
        self.intro_animation.setEasingCurve(QEasingCurve.Type.OutExpo) 
        self.intro_animation.setStartValue(0.0)
        self.intro_animation.setEndValue(1.0)

    def transition_to_index(self, next_index):
        self.pos_animation.stop()
        self.pos_animation.setStartValue(self.current_progress)
        self.pos_animation.setEndValue(float(next_index))
        self.pos_animation.start()

    def update_visual_state(self):
        idx = self.current_progress
        midpoint = 2.0
        distance = idx - midpoint
        
        base_x = float(self.controller.width() / 2) + (distance * 260.0)
        base_y = float(self.controller.height() / 2)
        
        base_scale = max(0.68, 1.0 - (abs(distance) * 0.12))
        
        # HYPER-SPEED BREACH SCALE: Cards erupt outward from 4.5x size scale limits down to base layouts
        intro_scale_modifier = 4.5 - (self.intro_progress * 3.5)
        total_scale = base_scale * self.current_hover_scale * intro_scale_modifier
            
        transform = QTransform()
        transform.translate(base_x, base_y)
        transform.scale(total_scale, total_scale)
        transform.translate(-110.0, -220.0) 
        self.setTransform(transform)
        
        opacity = (1.0 if (self.is_hovered or abs(distance) < 0.1) else max(0.80, 1.0 - (abs(distance) * 0.05))) * self.intro_progress
        self.setOpacity(opacity)
        
        z_values = [80, 90, 100, 90, 80]
        ui_idx = int(round(idx))
        z_val = z_values[ui_idx] if 0 <= ui_idx < 5 else 50
        if self.is_hovered:
            z_val += 50
        self.setZValue(z_val)

    def hoverEnterEvent(self, event):
        if self.intro_progress < 0.95: return
        self.is_hovered = True
        self.hover_animation.stop()
        self.hover_animation.setStartValue(self.current_hover_scale)
        self.hover_animation.setEndValue(1.15)
        self.hover_animation.start()

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.hover_animation.stop()
        self.hover_animation.setStartValue(self.current_hover_scale)
        self.hover_animation.setEndValue(1.0)
        self.hover_animation.start()
        self.controller.refresh_z_ordering()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.intro_progress >= 0.95:
            set_windows_wallpaper(self.file_path)
            self.controller.hide_overlay_safely()
class WallpaperSwitcherOverlay(QWidget):
    """Headless window container running persistent memory threads and 0ms visibility hotkeys."""
    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.all_files = []
        self.current_index = 0
        self.cards = []
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(0, 0, screen.width(), screen.height())
        
        self.scene = QGraphicsScene(0, 0, screen.width(), screen.height(), self)
        self.view = QGraphicsView(self.scene, self)
        self.view.setGeometry(0, 0, screen.width(), screen.height())
        self.view.setStyleSheet("background: #000000; border: none;")
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        self.load_and_precache_assets()
        
        # PERSISTENT SYSTEM HOOK: Registers global hotkey to pull pre-cached app directly out of RAM
        keyboard.add_hotkey('alt+w', self.show_overlay_instantly)

    def load_and_precache_assets(self):
        valid_exts = ('.png', '.jpg', '.jpeg', '.webp')
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)
            
        self.all_files = [os.path.join(self.folder_path, f) for f in os.listdir(self.folder_path) if f.lower().endswith(valid_exts)]
        self.all_files.sort(key=os.path.getmtime, reverse=True)
        self.all_files = self.all_files[:12]
        total_files = len(self.all_files)
        
        if total_files == 0: return
            
        card_w, card_h = 220, 440
        slant = card_w * 0.22
        
        path = QPainterPath()
        path.moveTo(slant, 0.0)
        path.lineTo(card_w, 0.0)
        path.lineTo(card_w - slant, card_h)
        path.lineTo(0.0, card_h)
        path.closeSubpath()
        
        for idx, file_path in enumerate(self.all_files):
            raw = QPixmap(file_path)
            scaled = raw.scaledToHeight(card_h, Qt.TransformationMode.SmoothTransformation)
            crop_x = max(0, (scaled.width() - card_w) // 2)
            slice_pixmap = scaled.copy(crop_x, 0, card_w, card_h)
            
            masked_pixmap = QPixmap(card_w, card_h)
            masked_pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(masked_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, slice_pixmap)
            painter.end()
            
            card_item = WallpaperGraphicsCard(file_path, masked_pixmap, self)
            self.scene.addItem(card_item)
            self.cards.append(card_item)
            
        self.reset_card_positions()

    def reset_card_positions(self):
        total_files = len(self.cards)
        if total_files == 0: return
        for ui_idx in range(5):
            offset = ui_idx - 2
            data_idx = (self.current_index + offset) % total_files
            self.cards[data_idx].current_progress = float(ui_idx)
            self.cards[data_idx].intro_progress = 0.0

    def show_overlay_instantly(self):
        """Triggers direct memory activation loop bypassing process instantiation lag."""
        self.show()
        self.raise_()
        self.activateWindow()
        
        total_files = len(self.cards)
        if total_files == 0: return
        
        self.master_intro_group = QParallelAnimationGroup()
        visible_indices = [(self.current_index + o) % total_files for o in range(-2, 3)]
        
        for idx in visible_indices:
            card = self.cards[idx]
            card.intro_animation.stop()
            card.intro_animation.setStartValue(0.0)
            card.intro_animation.setEndValue(1.0)
            self.master_intro_group.addAnimation(card.intro_animation)
            
        for idx, card in enumerate(self.cards):
            if idx not in visible_indices:
                card.setOpacity(0.0)
                card.setZValue(-1)
                
        self.refresh_z_ordering()
        self.master_intro_group.start()

    def hide_overlay_safely(self):
        """Hides the presentation layout window seamlessly while keeping active variables in cache."""
        self.hide()
        self.reset_card_positions()

    def refresh_carousel_indices(self):
        total_files = len(self.cards)
        if total_files == 0: return
        
        for ui_idx in range(5):
            offset = ui_idx - 2
            data_idx = (self.current_index + offset) % total_files
            card = self.cards[data_idx]
            card.intro_progress = 1.0
            card.transition_to_index(ui_idx)
            
        visible_indices = [(self.current_index + o) % total_files for o in range(-2, 3)]
        for idx, card in enumerate(self.cards):
            if idx not in visible_indices:
                card.setOpacity(0.0)
                card.setZValue(-1)
                
        self.refresh_z_ordering()

    def refresh_z_ordering(self):
        total_files = len(self.cards)
        if total_files == 0: return
        visible_cards = [self.cards[(self.current_index + o) % total_files] for o in range(-2, 3)]
        z_values = [80, 90, 100, 90, 80]
        for idx, card in enumerate(visible_cards):
            if not card.is_hovered:
                card.setZValue(z_values[idx])

    def wheelEvent(self, event):
        if not self.cards: return
        if hasattr(self, 'master_intro_group') and self.master_intro_group.state() == QAbstractAnimation.State.Running:
            return
            
        angle = event.angleDelta().y()
        if angle > 0:
            self.current_index = (self.current_index - 1) % len(self.cards)
        elif angle < 0:
            self.current_index = (self.current_index + 1) % len(self.cards)
        self.refresh_carousel_indices()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide_overlay_safely()

if __name__ == '__main__':
    wp_directory = os.path.expanduser("~/Pictures/Wallpapers")
    app = QApplication(sys.argv)
    ex = WallpaperSwitcherOverlay(wp_directory)
    # The application starts completely hidden, sleeping natively inside memory
    sys.exit(app.exec())
