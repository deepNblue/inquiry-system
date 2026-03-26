"""
价格趋势分析模块
趋势检测、预测、最佳购买时机建议
"""

import os
import json
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import sqlite3

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class TrendDirection(Enum):
    """趋势方向"""
    UP = "up"       # 上涨
    DOWN = "down"   # 下跌
    STABLE = "stable"  # 稳定
    UNKNOWN = "unknown"


@dataclass
class TrendAnalysis:
    """趋势分析结果"""
    product_name: str
    direction: TrendDirection
    avg_price: float
    min_price: float
    max_price: float
    price_range_pct: float  # 价格波动范围百分比
    volatility: str  # 波动性: low/medium/high
    
    # 移动平均
    ma_7days: float = 0
    ma_30days: float = 0
    
    # 趋势评分 (0-100)
    trend_score: int = 50  # >50 看涨, <50 看跌
    
    # 建议
    recommendation: str = ""  # buy/hold/wait
    recommendation_reason: str = ""
    
    # 置信度
    confidence: float = 0  # 0-1


class PricePredictor:
    """
    价格预测器
    基于历史数据进行趋势分析和预测
    """
    
    def __init__(self, db_path: str = "data/history.db"):
        self.db_path = db_path
        self.conn = None
        if db_path:
            self._connect()
    
    def _connect(self):
        """连接数据库"""
        if os.path.exists(self.db_path):
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
    
    def analyze_trend(
        self,
        product_name: str,
        brand: str = "",
        days: int = 30
    ) -> TrendAnalysis:
        """
        分析价格趋势
        
        Args:
            product_name: 产品名称
            brand: 品牌
            days: 分析天数
        
        Returns:
            趋势分析结果
        """
        # 获取历史数据
        prices = self._get_price_history(product_name, brand, days)
        
        if len(prices) < 3:
            return TrendAnalysis(
                product_name=product_name,
                direction=TrendDirection.UNKNOWN,
                avg_price=0,
                min_price=0,
                max_price=0,
                price_range_pct=0,
                volatility="unknown",
                recommendation="insufficient_data",
                recommendation_reason="历史数据不足"
            )
        
        # 计算统计指标
        price_values = [p["price"] for p in prices]
        
        avg_price = sum(price_values) / len(price_values)
        min_price = min(price_values)
        max_price = max(price_values)
        price_range_pct = (max_price - min_price) / avg_price * 100 if avg_price > 0 else 0
        
        # 计算波动性
        if HAS_NUMPY:
            volatility = self._calculate_volatility(price_values)
        else:
            volatility = self._simple_volatility(price_values)
        
        # 计算趋势方向
        direction = self._detect_direction(price_values)
        
        # 计算移动平均
        ma_7 = self._moving_average(price_values, 7)
        ma_30 = self._moving_average(price_values, 30)
        
        # 计算趋势评分
        trend_score = self._calculate_trend_score(price_values, direction)
        
        # 生成建议
        recommendation, reason = self._generate_recommendation(
            direction, trend_score, volatility, price_values[-1] if price_values else 0
        )
        
        return TrendAnalysis(
            product_name=product_name,
            direction=direction,
            avg_price=avg_price,
            min_price=min_price,
            max_price=max_price,
            price_range_pct=price_range_pct,
            volatility=volatility,
            ma_7days=ma_7,
            ma_30days=ma_30,
            trend_score=trend_score,
            recommendation=recommendation,
            recommendation_reason=reason,
            confidence=min(len(prices) / 30, 1.0)  # 数据量越多置信度越高
        )
    
    def _get_price_history(
        self,
        product_name: str,
        brand: str = "",
        days: int = 30
    ) -> List[Dict]:
        """获取价格历史"""
        if not self.conn:
            return []
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        if brand:
            cursor = self.conn.execute("""
                SELECT price, timestamp FROM price_history
                WHERE product_name LIKE ? AND brand LIKE ? AND timestamp >= ?
                ORDER BY timestamp
            """, (f"%{product_name}%", f"%{brand}%", cutoff))
        else:
            cursor = self.conn.execute("""
                SELECT price, timestamp FROM price_history
                WHERE product_name LIKE ? AND timestamp >= ?
                ORDER BY timestamp
            """, (f"%{product_name}%", cutoff))
        
        return [
            {"price": row[0], "timestamp": row[1]}
            for row in cursor.fetchall()
        ]
    
    def _calculate_volatility(self, prices: List[float]) -> str:
        """计算波动性"""
        if not HAS_NUMPY or len(prices) < 2:
            return self._simple_volatility(prices)
        
        arr = np.array(prices)
        returns = np.diff(arr) / arr[:-1]
        std = np.std(returns)
        
        # 日波动率分类
        if std < 0.02:
            return "low"
        elif std < 0.05:
            return "medium"
        else:
            return "high"
    
    def _simple_volatility(self, prices: List[float]) -> str:
        """简单波动性计算"""
        if len(prices) < 2:
            return "unknown"
        
        max_p = max(prices)
        min_p = min(prices)
        avg_p = sum(prices) / len(prices)
        
        volatility_pct = (max_p - min_p) / avg_p if avg_p > 0 else 0
        
        if volatility_pct < 0.05:
            return "low"
        elif volatility_pct < 0.15:
            return "medium"
        else:
            return "high"
    
    def _detect_direction(self, prices: List[float]) -> TrendDirection:
        """检测趋势方向"""
        if len(prices) < 3:
            return TrendDirection.UNKNOWN
        
        # 简单线性回归斜率
        n = len(prices)
        x = list(range(n))
        
        sum_x = sum(x)
        sum_y = sum(prices)
        sum_xy = sum(xi * yi for xi, yi in zip(x, prices))
        sum_xx = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x) if (n * sum_xx - sum_x * sum_x) != 0 else 0
        
        # 归一化斜率（相对于平均值）
        avg = sum(prices) / len(prices)
        normalized_slope = slope / avg if avg > 0 else 0
        
        if normalized_slope > 0.01:  # 1%以上上涨
            return TrendDirection.UP
        elif normalized_slope < -0.01:  # 1%以上下跌
            return TrendDirection.DOWN
        else:
            return TrendDirection.STABLE
    
    def _moving_average(self, prices: List[float], window: int) -> float:
        """计算移动平均"""
        if len(prices) < window:
            return sum(prices) / len(prices) if prices else 0
        
        return sum(prices[-window:]) / window
    
    def _calculate_trend_score(self, prices: List[float], direction: TrendDirection) -> int:
        """计算趋势评分 (0-100)"""
        if len(prices) < 2:
            return 50
        
        # 基准：50为中性
        base_score = 50
        
        # 根据方向调整
        if direction == TrendDirection.UP:
            base_score += 20
        elif direction == TrendDirection.DOWN:
            base_score -= 20
        
        # 根据近期vs远期对比调整
        if len(prices) >= 7:
            recent_avg = sum(prices[-7:]) / 7
            older_avg = sum(prices[:7]) / 7 if len(prices) >= 14 else sum(prices) / len(prices)
            
            if recent_avg < older_avg:
                base_score -= 10  # 近期下跌
            else:
                base_score += 10  # 近期上涨
        
        # 限制范围
        return max(0, min(100, base_score))
    
    def _generate_recommendation(
        self,
        direction: TrendDirection,
        trend_score: int,
        volatility: str,
        current_price: float
    ) -> Tuple[str, str]:
        """生成采购建议"""
        # 建议逻辑
        if trend_score < 35:
            # 趋势看跌
            return "wait", "价格可能继续下行，建议观望"
        elif trend_score > 65:
            # 趋势看涨
            if direction == TrendDirection.UP:
                return "buy", "价格正在上涨，建议尽早购买"
            else:
                return "hold", "价格处于相对低位，可考虑购买"
        elif volatility == "high":
            # 高波动
            return "wait", "价格波动较大，建议等待稳定后再购买"
        else:
            # 中性
            return "hold", "价格走势平稳，可根据需求购买"
    
    def predict_price(
        self,
        product_name: str,
        brand: str = "",
        days_ahead: int = 7
    ) -> Dict:
        """
        预测未来价格
        
        Args:
            product_name: 产品名称
            brand: 品牌
            days_ahead: 预测天数
        
        Returns:
            预测结果
        """
        analysis = self.analyze_trend(product_name, brand)
        
        if analysis.direction == TrendDirection.UNKNOWN:
            return {
                "product_name": product_name,
                "predicted_price": analysis.avg_price,
                "prediction": "unknown",
                "confidence": 0
            }
        
        # 简单线性预测
        prices = self._get_price_history(product_name, brand, 30)
        if len(prices) < 3:
            return {
                "product_name": product_name,
                "predicted_price": analysis.avg_price,
                "prediction": "insufficient_data",
                "confidence": 0
            }
        
        price_values = [p["price"] for p in prices]
        
        # 简单线性回归
        n = len(price_values)
        x = list(range(n))
        y = price_values
        
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_xx = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x) if (n * sum_xx - sum_x * sum_x) != 0 else 0
        intercept = (sum_y - slope * sum_x) / n
        
        # 预测
        future_x = n + days_ahead
        predicted = slope * future_x + intercept
        
        # 确保预测值合理
        predicted = max(predicted, analysis.min_price * 0.8)
        predicted = min(predicted, analysis.max_price * 1.2)
        
        # 预测方向
        if slope > 0:
            prediction = "rising"
        elif slope < 0:
            prediction = "falling"
        else:
            prediction = "stable"
        
        return {
            "product_name": product_name,
            "current_price": price_values[-1] if price_values else 0,
            "predicted_price": round(predicted, 2),
            "prediction": prediction,
            "days_ahead": days_ahead,
            "confidence": analysis.confidence * 0.8  # 预测置信度更低
        }
    
    def batch_analyze(
        self,
        products: List[str],
        days: int = 30
    ) -> List[TrendAnalysis]:
        """批量分析趋势"""
        results = []
        for product in products:
            if isinstance(product, dict):
                name = product.get("name", "")
                brand = product.get("brand", "")
            else:
                name = product
                brand = ""
            
            analysis = self.analyze_trend(name, brand, days)
            results.append(analysis)
        
        return results
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()


# 便捷函数
def analyze(product_name: str, brand: str = "") -> TrendAnalysis:
    """快速趋势分析"""
    predictor = PricePredictor()
    result = predictor.analyze_trend(product_name, brand)
    predictor.close()
    return result


def predict(product_name: str, days: int = 7) -> Dict:
    """快速价格预测"""
    predictor = PricePredictor()
    result = predictor.predict_price(product_name, days_ahead=days)
    predictor.close()
    return result
