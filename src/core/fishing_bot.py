"""
钓鱼机器人核心逻辑
实现钓鱼状态机，协调声音检测和按键发送
"""

import threading
import time
from enum import Enum, auto
from typing import Callable, Optional
from dataclasses import dataclass

from .key_sender import KeySender
from .sound_detector import SoundDetector
from ..utils.config import Config


class FishingState(Enum):
    """钓鱼状态枚举"""
    IDLE = auto()        # 空闲状态
    PRE_ACTION = auto()  # 执行前置动作（上饵）
    CASTING = auto()     # 抛竿中
    WAITING = auto()     # 等待鱼上钩
    HOOKING = auto()     # 收杆中
    PAUSED = auto()      # 暂停状态


@dataclass
class FishingStats:
    """钓鱼统计数据"""
    total_casts: int = 0      # 总抛竿次数
    successful_hooks: int = 0  # 成功收杆次数
    timeouts: int = 0         # 超时次数
    baits_applied: int = 0    # 上饵次数
    start_time: float = 0     # 开始时间
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_casts == 0:
            return 0.0
        return self.successful_hooks / self.total_casts * 100
    
    @property
    def running_time(self) -> float:
        """运行时间（秒）"""
        if self.start_time == 0:
            return 0
        return time.time() - self.start_time
    
    def reset(self) -> None:
        """重置统计"""
        self.total_casts = 0
        self.successful_hooks = 0
        self.timeouts = 0
        self.baits_applied = 0
        self.start_time = 0


class FishingBot:
    """钓鱼机器人"""
    
    def __init__(self, config: Optional[Config] = None):
        """
        初始化钓鱼机器人
        
        Args:
            config: 配置对象，默认使用默认配置
        """
        self._config = config or Config()
        
        # 核心组件
        self._key_sender = KeySender()
        self._sound_detector = SoundDetector(
            threshold=self._config.sound_threshold,
            callback=self._on_sound_detected
        )
        
        # 状态
        self._state = FishingState.IDLE
        self._running = False
        self._paused = False
        
        # 统计
        self._stats = FishingStats()
        
        # 线程
        self._main_thread: Optional[threading.Thread] = None
        self._timer_thread: Optional[threading.Thread] = None
        
        # 时间追踪
        self._last_cast_time = 0
        self._last_bait_time = 0
        self._waiting_start_time = 0
        
        # 声音检测标志
        self._sound_detected = threading.Event()
        
        # 回调
        self._state_callback: Optional[Callable[[FishingState], None]] = None
        self._stats_callback: Optional[Callable[[FishingStats], None]] = None
        self._log_callback: Optional[Callable[[str], None]] = None
    
    @property
    def state(self) -> FishingState:
        """获取当前状态"""
        return self._state
    
    @property
    def stats(self) -> FishingStats:
        """获取统计数据"""
        return self._stats
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
    
    @property
    def is_paused(self) -> bool:
        """是否暂停"""
        return self._paused
    
    @property
    def config(self) -> Config:
        """获取配置"""
        return self._config
    
    @property
    def sound_detector(self) -> SoundDetector:
        """获取声音检测器"""
        return self._sound_detector
    
    def set_config(self, config: Config) -> None:
        """设置配置"""
        self._config = config
        self._sound_detector.threshold = config.calculate_threshold_from_sensitivity()
    
    def set_state_callback(self, callback: Callable[[FishingState], None]) -> None:
        """设置状态变化回调"""
        self._state_callback = callback
    
    def set_stats_callback(self, callback: Callable[[FishingStats], None]) -> None:
        """设置统计更新回调"""
        self._stats_callback = callback
    
    def set_log_callback(self, callback: Callable[[str], None]) -> None:
        """设置日志回调"""
        self._log_callback = callback
    
    def _log(self, message: str) -> None:
        """记录日志"""
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        if self._log_callback:
            self._log_callback(log_msg)
    
    def _set_state(self, state: FishingState) -> None:
        """设置状态并触发回调"""
        self._state = state
        if self._state_callback:
            self._state_callback(state)
    
    def _update_stats(self) -> None:
        """更新统计并触发回调"""
        if self._stats_callback:
            self._stats_callback(self._stats)
    
    def _on_sound_detected(self) -> None:
        """声音检测回调"""
        if self._state == FishingState.WAITING:
            self._sound_detected.set()
    
    def _do_pre_action(self) -> None:
        """执行前置动作（上饵等）"""
        self._set_state(FishingState.PRE_ACTION)
        self._log("执行前置动作...")
        
        # 按下前置动作键
        self._key_sender.press_key(self._config.pre_action_key)
        self._stats.baits_applied += 1
        self._last_bait_time = time.time()
        
        # 等待动作完成（上饵需要一些时间）
        KeySender.sleep_random(2000, 3000)
        
        self._update_stats()
    
    def _do_cast(self) -> None:
        """执行抛竿"""
        self._set_state(FishingState.CASTING)
        self._log("抛竿中...")
        
        # 按下钓鱼键
        self._key_sender.press_key(self._config.fishing_key)
        self._stats.total_casts += 1
        self._last_cast_time = time.time()
        
        # 等待抛竿动画完成
        KeySender.sleep_random(1500, 2500)
        
        self._update_stats()
    
    def _do_hook(self) -> None:
        """执行收杆"""
        self._set_state(FishingState.HOOKING)
        self._log("检测到鱼上钩，收杆!")
        
        # 随机延迟后按下交互键
        delay_min, delay_max = self._config.get_hook_delay_range()
        KeySender.sleep_random(delay_min, delay_max)
        
        self._key_sender.press_key(self._config.interact_key)
        self._stats.successful_hooks += 1
        
        # 收杆后延迟
        cast_delay_min, cast_delay_max = self._config.get_cast_delay_range()
        KeySender.sleep_random(cast_delay_min, cast_delay_max)
        
        self._update_stats()
    
    def _check_need_bait(self) -> bool:
        """检查是否需要上饵"""
        if self._last_bait_time == 0:
            return True
        
        elapsed = time.time() - self._last_bait_time
        return elapsed >= self._config.bait_interval
    
    def _main_loop(self) -> None:
        """主循环"""
        self._stats.start_time = time.time()
        
        while self._running:
            # 检查暂停
            if self._paused:
                time.sleep(0.1)
                continue
            
            try:
                # 检查是否需要上饵
                if self._check_need_bait():
                    self._do_pre_action()
                    if not self._running:
                        break
                
                # 抛竿
                self._do_cast()
                if not self._running:
                    break
                
                # 等待鱼上钩
                self._set_state(FishingState.WAITING)
                self._waiting_start_time = time.time()
                self._sound_detected.clear()
                self._log("等待鱼上钩...")
                
                # 等待声音或超时
                detected = self._sound_detected.wait(timeout=self._config.timeout)
                
                if not self._running:
                    break
                
                if detected:
                    # 检测到声音，收杆
                    self._do_hook()
                else:
                    # 超时
                    self._log("超时，重新抛竿")
                    self._stats.timeouts += 1
                    self._update_stats()
                
            except Exception as e:
                self._log(f"错误: {e}")
                time.sleep(1)
        
        self._set_state(FishingState.IDLE)
    
    def start(self) -> bool:
        """
        开始钓鱼
        
        Returns:
            是否成功启动
        """
        if self._running:
            return True
        
        # 启动声音检测
        self._sound_detector.threshold = self._config.calculate_threshold_from_sensitivity()
        if not self._sound_detector.start():
            self._log("声音检测启动失败")
            return False
        
        self._running = True
        self._paused = False
        self._stats.reset()
        
        # 启动主线程
        self._main_thread = threading.Thread(target=self._main_loop, daemon=True)
        self._main_thread.start()
        
        self._log("钓鱼机器人已启动")
        return True
    
    def stop(self) -> None:
        """停止钓鱼"""
        self._running = False
        self._paused = False
        self._sound_detected.set()  # 唤醒等待中的线程
        
        # 停止声音检测
        self._sound_detector.stop()
        
        # 等待主线程结束
        if self._main_thread and self._main_thread.is_alive():
            self._main_thread.join(timeout=2)
        
        self._set_state(FishingState.IDLE)
        self._log("钓鱼机器人已停止")
    
    def pause(self) -> None:
        """暂停钓鱼"""
        if self._running and not self._paused:
            self._paused = True
            self._set_state(FishingState.PAUSED)
            self._log("已暂停")
    
    def resume(self) -> None:
        """恢复钓鱼"""
        if self._running and self._paused:
            self._paused = False
            self._log("已恢复")
    
    def toggle_pause(self) -> None:
        """切换暂停状态"""
        if self._paused:
            self.resume()
        else:
            self.pause()
    
    def calibrate_sound(self, duration: float = 2.0) -> float:
        """
        校准声音
        
        Args:
            duration: 校准时长
            
        Returns:
            噪音基准值
        """
        was_running = self._running
        
        if not self._sound_detector.is_running:
            self._sound_detector.start()
        
        self._log(f"正在校准声音（{duration}秒）...")
        noise_floor = self._sound_detector.calibrate(duration)
        self._log(f"校准完成，噪音基准: {noise_floor:.4f}")
        
        if not was_running:
            self._sound_detector.stop()
        
        return noise_floor
