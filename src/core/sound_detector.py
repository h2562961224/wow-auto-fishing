"""
声音检测模块
使用 sounddevice 监听系统音频输出，检测鱼上钩的声音
支持 Windows (WASAPI Loopback) 和 macOS (BlackHole/Soundflower)
"""

import platform
import threading
import time
from typing import Callable, Optional, List
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None
    print("警告: sounddevice 未安装，声音检测功能将不可用")


# 系统类型
IS_MACOS = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"


class SoundDetector:
    """声音检测器"""
    
    # macOS 常见虚拟音频设备关键词
    MACOS_VIRTUAL_DEVICES = [
        'blackhole',
        'soundflower',
        'loopback',
        'virtual',
        'multi-output',
    ]
    
    # Windows 常见 loopback 设备关键词
    WINDOWS_LOOPBACK_DEVICES = [
        'loopback',
        'stereo mix',
        'what u hear',
        '立体声混音',
        'wave out',
    ]
    
    def __init__(
        self,
        threshold: float = 0.02,
        callback: Optional[Callable[[], None]] = None,
        sample_rate: int = 44100,
        block_size: int = 1024
    ):
        """
        初始化声音检测器
        
        Args:
            threshold: 音量阈值（0-1），超过此值触发回调
            callback: 检测到声音时的回调函数
            sample_rate: 采样率
            block_size: 每次处理的采样数
        """
        self._threshold = threshold
        self._callback = callback
        self._sample_rate = sample_rate
        self._block_size = block_size
        
        self._running = False
        self._stream: Optional[sd.InputStream] = None
        self._thread: Optional[threading.Thread] = None
        
        # 用于防止重复触发
        self._last_trigger_time = 0
        self._trigger_cooldown = 1.0  # 触发冷却时间（秒）
        
        # 当前音量（用于 UI 显示）
        self._current_volume = 0.0
        
        # 背景噪音基准
        self._noise_floor = 0.0
        self._calibrating = False
        self._calibration_samples: List[float] = []
        
        # 音频设备
        self._device_index: Optional[int] = None
        self._device_name: str = ""
    
    @property
    def threshold(self) -> float:
        """获取当前阈值"""
        return self._threshold
    
    @threshold.setter
    def threshold(self, value: float) -> None:
        """设置阈值"""
        self._threshold = max(0.001, min(1.0, value))
    
    @property
    def current_volume(self) -> float:
        """获取当前音量"""
        return self._current_volume
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
    
    def set_callback(self, callback: Callable[[], None]) -> None:
        """设置回调函数"""
        self._callback = callback
    
    def set_trigger_cooldown(self, seconds: float) -> None:
        """设置触发冷却时间"""
        self._trigger_cooldown = seconds
    
    @staticmethod
    def get_audio_devices() -> List[dict]:
        """
        获取可用的音频设备列表
        
        Returns:
            设备信息列表
        """
        if sd is None:
            return []
        
        devices = []
        try:
            device_list = sd.query_devices()
            for i, device in enumerate(device_list):
                # 只获取输入设备（包括 loopback）
                if device['max_input_channels'] > 0:
                    devices.append({
                        'index': i,
                        'name': device['name'],
                        'channels': device['max_input_channels'],
                        'sample_rate': device['default_samplerate'],
                        'is_virtual': SoundDetector._is_virtual_device(device['name'])
                    })
        except Exception as e:
            print(f"获取音频设备失败: {e}")
        
        return devices
    
    @staticmethod
    def _is_virtual_device(name: str) -> bool:
        """检查是否为虚拟音频设备"""
        name_lower = name.lower()
        
        if IS_MACOS:
            return any(kw in name_lower for kw in SoundDetector.MACOS_VIRTUAL_DEVICES)
        elif IS_WINDOWS:
            return any(kw in name_lower for kw in SoundDetector.WINDOWS_LOOPBACK_DEVICES)
        
        return False
    
    @staticmethod
    def get_loopback_device() -> tuple[Optional[int], str]:
        """
        获取系统音频回环设备
        Windows: WASAPI loopback
        macOS: BlackHole/Soundflower 等虚拟音频设备
        
        Returns:
            (设备索引, 设备名称)，未找到返回 (None, "")
        """
        if sd is None:
            return None, ""
        
        try:
            devices = sd.query_devices()
            
            # 根据平台选择关键词
            if IS_MACOS:
                keywords = SoundDetector.MACOS_VIRTUAL_DEVICES
            else:
                keywords = SoundDetector.WINDOWS_LOOPBACK_DEVICES
            
            for i, device in enumerate(devices):
                name = device['name'].lower()
                if device['max_input_channels'] > 0:
                    for keyword in keywords:
                        if keyword in name:
                            return i, device['name']
        except Exception as e:
            print(f"查找 loopback 设备失败: {e}")
        
        return None, ""
    
    @staticmethod
    def get_recommended_device() -> tuple[Optional[int], str]:
        """
        获取推荐的音频输入设备
        优先返回虚拟音频设备，否则返回默认输入设备
        
        Returns:
            (设备索引, 设备名称)
        """
        # 先尝试找虚拟设备
        device_idx, device_name = SoundDetector.get_loopback_device()
        if device_idx is not None:
            return device_idx, device_name
        
        # 没找到就用默认输入设备
        if sd is not None:
            try:
                default = sd.query_devices(kind='input')
                if default:
                    return default['index'], default['name']
            except Exception:
                pass
        
        return None, ""
    
    def set_device(self, device_index: Optional[int], device_name: str = "") -> None:
        """设置音频设备"""
        self._device_index = device_index
        self._device_name = device_name
    
    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """
        音频流回调函数
        
        Args:
            indata: 输入音频数据
            frames: 帧数
            time_info: 时间信息
            status: 状态
        """
        if status:
            print(f"音频状态: {status}")
        
        # 计算 RMS 音量
        volume = np.sqrt(np.mean(indata ** 2))
        self._current_volume = float(volume)
        
        # 校准模式
        if self._calibrating:
            self._calibration_samples.append(volume)
            return
        
        # 检测是否超过阈值
        current_time = time.time()
        effective_threshold = self._threshold + self._noise_floor
        
        if (volume > effective_threshold and 
            current_time - self._last_trigger_time > self._trigger_cooldown):
            self._last_trigger_time = current_time
            if self._callback:
                # 在新线程中调用回调，避免阻塞音频流
                threading.Thread(target=self._callback, daemon=True).start()
    
    def start(self) -> bool:
        """
        开始监听
        
        Returns:
            是否成功启动
        """
        if sd is None:
            print("sounddevice 未安装")
            return False
        
        if self._running:
            return True
        
        try:
            # 确定使用的设备
            device = self._device_index
            device_name = self._device_name
            
            if device is None:
                device, device_name = self.get_recommended_device()
            
            if device is None:
                print("未找到可用的音频输入设备")
                if IS_MACOS:
                    print("提示: macOS 需要安装 BlackHole 等虚拟音频设备来捕获系统声音")
                else:
                    print("提示: Windows 需要启用立体声混音 (Stereo Mix)")
                return False
            
            self._stream = sd.InputStream(
                device=device,
                channels=1,
                samplerate=self._sample_rate,
                blocksize=self._block_size,
                callback=self._audio_callback
            )
            self._stream.start()
            self._running = True
            self._device_index = device
            self._device_name = device_name
            print(f"声音检测已启动，设备: {device_name} (索引: {device})")
            return True
        except Exception as e:
            print(f"启动声音检测失败: {e}")
            if IS_MACOS:
                print("提示: 请确保已安装 BlackHole 并在系统偏好设置中正确配置")
            return False
    
    def stop(self) -> None:
        """停止监听"""
        self._running = False
        
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                print(f"停止音频流失败: {e}")
            finally:
                self._stream = None
    
    def calibrate(self, duration: float = 2.0) -> float:
        """
        校准背景噪音
        
        Args:
            duration: 校准时长（秒）
            
        Returns:
            校准后的噪音基准值
        """
        if not self._running:
            print("请先启动声音检测")
            return 0.0
        
        self._calibrating = True
        self._calibration_samples = []
        
        # 等待采样
        time.sleep(duration)
        
        self._calibrating = False
        
        if self._calibration_samples:
            # 使用平均值的 1.5 倍作为噪音基准
            self._noise_floor = np.mean(self._calibration_samples) * 1.5
            print(f"噪音基准: {self._noise_floor:.4f}")
        
        return self._noise_floor
    
    def reset_calibration(self) -> None:
        """重置校准"""
        self._noise_floor = 0.0
