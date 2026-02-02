"""
配置管理模块
负责加载和保存用户配置
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Config:
    """配置数据类"""
    
    # 快捷键设置
    pre_action_key: str = "1"       # 前置动作键（上饵等）
    fishing_key: str = "2"          # 钓鱼键（抛竿）
    interact_key: str = "f"         # 交互键（收杆）
    
    # 时间设置（秒）
    bait_interval: int = 900        # 上饵间隔（默认15分钟=900秒）
    timeout: int = 20               # 超时时间（秒）
    
    # 延迟设置（毫秒）
    hook_delay_min: int = 200       # 检测到声音后最小延迟
    hook_delay_max: int = 600       # 检测到声音后最大延迟
    cast_delay_min: int = 500       # 收杆后最小延迟
    cast_delay_max: int = 1500      # 收杆后最大延迟
    
    # 声音检测设置
    sound_threshold: float = 0.02   # 声音阈值（0-1）
    sound_sensitivity: int = 50     # 灵敏度（0-100）
    
    # 配置文件路径
    _config_path: str = "config.json"
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """
        从文件加载配置
        
        Args:
            config_path: 配置文件路径，默认为 config.json
            
        Returns:
            Config 实例
        """
        path = config_path or cls._config_path
        
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 过滤掉私有属性
                    filtered_data = {k: v for k, v in data.items() if not k.startswith('_')}
                    config = cls(**filtered_data)
                    config._config_path = path
                    return config
            except (json.JSONDecodeError, TypeError) as e:
                print(f"配置文件加载失败，使用默认配置: {e}")
        
        config = cls()
        config._config_path = path
        return config
    
    def save(self, config_path: Optional[str] = None) -> bool:
        """
        保存配置到文件
        
        Args:
            config_path: 配置文件路径，默认为当前配置路径
            
        Returns:
            是否保存成功
        """
        path = config_path or self._config_path
        
        try:
            data = asdict(self)
            # 移除私有属性
            data = {k: v for k, v in data.items() if not k.startswith('_')}
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"配置保存失败: {e}")
            return False
    
    def update(self, **kwargs) -> None:
        """
        更新配置项
        
        Args:
            **kwargs: 要更新的配置项
        """
        for key, value in kwargs.items():
            if hasattr(self, key) and not key.startswith('_'):
                setattr(self, key, value)
    
    def get_hook_delay_range(self) -> tuple[int, int]:
        """获取收杆延迟范围（毫秒）"""
        return (self.hook_delay_min, self.hook_delay_max)
    
    def get_cast_delay_range(self) -> tuple[int, int]:
        """获取抛竿延迟范围（毫秒）"""
        return (self.cast_delay_min, self.cast_delay_max)
    
    def calculate_threshold_from_sensitivity(self) -> float:
        """
        根据灵敏度计算阈值
        灵敏度越高，阈值越低（越容易触发）
        
        Returns:
            计算后的阈值
        """
        # 灵敏度 0-100 映射到阈值 0.1-0.005
        # 线性映射：sensitivity=0 -> threshold=0.1, sensitivity=100 -> threshold=0.005
        max_threshold = 0.1
        min_threshold = 0.005
        self.sound_threshold = max_threshold - (self.sound_sensitivity / 100) * (max_threshold - min_threshold)
        return self.sound_threshold
