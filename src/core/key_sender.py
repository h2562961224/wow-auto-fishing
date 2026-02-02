"""
按键发送模块
负责模拟键盘按键发送到游戏窗口
"""

import random
import time
from typing import Optional
from pynput.keyboard import Key, Controller, KeyCode


class KeySender:
    """按键发送器"""
    
    # 特殊按键映射
    SPECIAL_KEYS = {
        'space': Key.space,
        'enter': Key.enter,
        'tab': Key.tab,
        'esc': Key.esc,
        'escape': Key.esc,
        'backspace': Key.backspace,
        'delete': Key.delete,
        'up': Key.up,
        'down': Key.down,
        'left': Key.left,
        'right': Key.right,
        'home': Key.home,
        'end': Key.end,
        'pageup': Key.page_up,
        'pagedown': Key.page_down,
        'f1': Key.f1,
        'f2': Key.f2,
        'f3': Key.f3,
        'f4': Key.f4,
        'f5': Key.f5,
        'f6': Key.f6,
        'f7': Key.f7,
        'f8': Key.f8,
        'f9': Key.f9,
        'f10': Key.f10,
        'f11': Key.f11,
        'f12': Key.f12,
        'shift': Key.shift,
        'ctrl': Key.ctrl,
        'alt': Key.alt,
    }
    
    def __init__(self):
        """初始化按键控制器"""
        self._keyboard = Controller()
        self._enabled = True
    
    def set_enabled(self, enabled: bool) -> None:
        """
        设置是否启用按键发送
        
        Args:
            enabled: 是否启用
        """
        self._enabled = enabled
    
    def _parse_key(self, key_str: str) -> Key | KeyCode:
        """
        解析按键字符串
        
        Args:
            key_str: 按键字符串，如 'a', 'f1', 'space' 等
            
        Returns:
            pynput 按键对象
        """
        key_lower = key_str.lower().strip()
        
        # 检查是否为特殊按键
        if key_lower in self.SPECIAL_KEYS:
            return self.SPECIAL_KEYS[key_lower]
        
        # 普通字符按键
        if len(key_str) == 1:
            return KeyCode.from_char(key_str.lower())
        
        # 尝试作为虚拟键码
        raise ValueError(f"无法识别的按键: {key_str}")
    
    def press_key(self, key_str: str) -> bool:
        """
        按下并释放一个按键
        
        Args:
            key_str: 按键字符串
            
        Returns:
            是否成功
        """
        if not self._enabled:
            return False
        
        try:
            key = self._parse_key(key_str)
            self._keyboard.press(key)
            # 短暂延迟模拟真实按键
            time.sleep(random.uniform(0.05, 0.15))
            self._keyboard.release(key)
            return True
        except Exception as e:
            print(f"按键发送失败 [{key_str}]: {e}")
            return False
    
    def press_key_with_delay(
        self, 
        key_str: str, 
        delay_min_ms: int = 0, 
        delay_max_ms: int = 0
    ) -> bool:
        """
        延迟后按下按键
        
        Args:
            key_str: 按键字符串
            delay_min_ms: 最小延迟（毫秒）
            delay_max_ms: 最大延迟（毫秒）
            
        Returns:
            是否成功
        """
        if delay_max_ms > 0:
            delay_ms = random.randint(delay_min_ms, delay_max_ms)
            time.sleep(delay_ms / 1000.0)
        
        return self.press_key(key_str)
    
    def hold_key(self, key_str: str, duration_ms: int) -> bool:
        """
        按住按键一段时间
        
        Args:
            key_str: 按键字符串
            duration_ms: 按住时间（毫秒）
            
        Returns:
            是否成功
        """
        if not self._enabled:
            return False
        
        try:
            key = self._parse_key(key_str)
            self._keyboard.press(key)
            time.sleep(duration_ms / 1000.0)
            self._keyboard.release(key)
            return True
        except Exception as e:
            print(f"按键按住失败 [{key_str}]: {e}")
            return False
    
    @staticmethod
    def get_random_delay(min_ms: int, max_ms: int) -> float:
        """
        获取随机延迟时间（秒）
        
        Args:
            min_ms: 最小延迟（毫秒）
            max_ms: 最大延迟（毫秒）
            
        Returns:
            延迟时间（秒）
        """
        return random.randint(min_ms, max_ms) / 1000.0
    
    @staticmethod
    def sleep_random(min_ms: int, max_ms: int) -> None:
        """
        随机延迟
        
        Args:
            min_ms: 最小延迟（毫秒）
            max_ms: 最大延迟（毫秒）
        """
        delay = random.randint(min_ms, max_ms) / 1000.0
        time.sleep(delay)
