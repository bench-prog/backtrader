#!/usr/bin/env python3
"""
AI增强决策系统
实现基于机器学习和深度学习的智能交易决策
"""

import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import StandardScaler

import backtrader as bt

warnings.filterwarnings("ignore")


@dataclass
class MLFeatures:
    """机器学习特征"""

    price_features: List[float]
    volume_features: List[float]
    technical_features: List[float]
    market_regime: int  # 0: 震荡, 1: 趋势
    volatility_level: float
    trend_strength: float


class FeatureExtractor:
    """特征提取器"""

    def __init__(self, lookback_periods: List[int] = [5, 10, 20]):
        self.lookback_periods = lookback_periods
        self.scaler = StandardScaler()

    def extract_features(self, data: bt.DataBase) -> MLFeatures:
        """提取交易特征"""
        if len(data) < max(self.lookback_periods):
            # 数据不足时返回默认特征
            return MLFeatures(
                price_features=[0.0] * 12,
                volume_features=[0.0] * 6,
                technical_features=[0.0] * 8,
                market_regime=0,
                volatility_level=0.02,
                trend_strength=0.5,
            )

        # 价格特征
        price_features = self._extract_price_features(data)

        # 成交量特征
        volume_features = self._extract_volume_features(data)

        # 技术指标特征
        technical_features = self._extract_technical_features(data)

        # 市场状态特征
        market_features = self._extract_market_regime(data)

        return MLFeatures(
            price_features=price_features,
            volume_features=volume_features,
            technical_features=technical_features,
            market_regime=market_features["regime"],
            volatility_level=market_features["volatility"],
            trend_strength=market_features["trend_strength"],
        )

    def _extract_price_features(self, data: bt.DataBase) -> List[float]:
        """提取价格特征"""
        features = []

        for period in self.lookback_periods:
            if len(data) >= period:
                # 价格变化率
                price_change = (data.close[0] - data.close[-period]) / data.close[
                    -period
                ]
                features.append(price_change)

                # 价格波动率
                prices = [data.close[i] for i in range(-period, 1)]
                returns = np.diff(np.log(prices))
                volatility = np.std(returns)
                features.append(volatility)

                # 最高价/最低价比率
                highs = [data.high[i] for i in range(-period, 1)]
                lows = [data.low[i] for i in range(-period, 1)]
                hl_ratio = (max(highs) - min(lows)) / min(lows)
                features.append(hl_ratio)
            else:
                features.extend([0.0, 0.0, 0.0])

        return features

    def _extract_volume_features(self, data: bt.DataBase) -> List[float]:
        """提取成交量特征"""
        features = []

        for period in self.lookback_periods:
            if len(data) >= period:
                volumes = [data.volume[i] for i in range(-period, 1)]

                # 成交量变化率
                vol_change = (
                    (volumes[-1] - volumes[0]) / volumes[0] if volumes[0] > 0 else 0
                )
                features.append(vol_change)

                # 成交量波动率
                vol_std = (
                    np.std(volumes) / np.mean(volumes) if np.mean(volumes) > 0 else 0
                )
                features.append(vol_std)
            else:
                features.extend([0.0, 0.0])

        return features

    def _extract_technical_features(self, data: bt.DataBase) -> List[float]:
        """提取技术指标特征"""
        features = []

        # 简单移动平均线
        if len(data) >= 20:
            sma_10 = np.mean([data.close[i] for i in range(-10, 0)])
            sma_20 = np.mean([data.close[i] for i in range(-20, 0)])
            sma_ratio = sma_10 / sma_20 if sma_20 > 0 else 1
            features.append(sma_ratio)
        else:
            features.append(1.0)

        # RSI指标
        if len(data) >= 15:
            prices = [data.close[i] for i in range(-15, 0)]
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains)
            avg_loss = np.mean(losses)
            rs = avg_gain / avg_loss if avg_loss > 0 else 1
            rsi = 100 - (100 / (1 + rs))
            features.append(rsi / 100)  # 归一化到0-1
        else:
            features.append(0.5)

        # 布林带位置
        if len(data) >= 20:
            prices = [data.close[i] for i in range(-20, 0)]
            sma = np.mean(prices)
            std = np.std(prices)
            upper_band = sma + 2 * std
            lower_band = sma - 2 * std
            current_price = data.close[0]

            if upper_band > lower_band:
                bb_position = (current_price - lower_band) / (upper_band - lower_band)
                features.append(bb_position)
            else:
                features.append(0.5)
        else:
            features.append(0.5)

        # MACD指标（简化版）
        if len(data) >= 26:
            ema_12 = self._calculate_ema([data.close[i] for i in range(-12, 0)], 12)
            ema_26 = self._calculate_ema([data.close[i] for i in range(-26, 0)], 26)
            macd = (ema_12 - ema_26) / data.close[0] if data.close[0] > 0 else 0
            features.append(macd)
        else:
            features.append(0.0)

        return features

    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """计算指数移动平均"""
        if len(prices) == 0:
            return 0.0
        alpha = 2.0 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema

    def _extract_market_regime(self, data: bt.DataBase) -> Dict[str, Any]:
        """提取市场制度特征"""
        if len(data) < 20:
            return {"regime": 0, "volatility": 0.02, "trend_strength": 0.5}

        # 计算波动率
        prices = [data.close[i] for i in range(-20, 0)]
        returns = np.diff(np.log(prices))
        volatility = np.std(returns)

        # 计算趋势强度
        sma_5 = np.mean(prices[-5:]) if len(prices) >= 5 else prices[-1]
        sma_20 = np.mean(prices)
        trend_strength = abs(sma_5 - sma_20) / sma_20 if sma_20 > 0 else 0

        # 判断市场制度（简化）
        regime = 1 if trend_strength > 0.02 and volatility < 0.05 else 0

        return {
            "regime": regime,
            "volatility": volatility,
            "trend_strength": min(1.0, trend_strength * 10),
        }


class EnsemblePredictor:
    """集成预测器"""

    def __init__(self):
        self.models = {
            "rf": RandomForestClassifier(n_estimators=50, random_state=42),
            "gb": GradientBoostingClassifier(n_estimators=50, random_state=42),
        }
        self.is_trained = False
        self.feature_extractor = FeatureExtractor()

    def prepare_training_data(
        self, data: bt.DataBase, lookback_days: int = 100
    ) -> Tuple[np.ndarray, np.ndarray]:
        """准备训练数据"""
        if len(data) < lookback_days + 5:
            return np.array([]), np.array([])

        X, y = [], []

        # 使用历史数据训练
        for i in range(lookback_days, len(data) - 1):
            # 提取特征
            temp_data = type(data)()
            temp_data.lines = data.lines
            temp_data._idx = i

            features = self.feature_extractor.extract_features(temp_data)
            feature_vector = (
                features.price_features
                + features.volume_features
                + features.technical_features
                + [
                    features.market_regime,
                    features.volatility_level,
                    features.trend_strength,
                ]
            )

            # 标注标签（未来1天收益）
            future_return = (data.close[i + 1] - data.close[i]) / data.close[i]
            label = (
                1 if future_return > 0.005 else (-1 if future_return < -0.005 else 0)
            )

            X.append(feature_vector)
            y.append(label)

        return np.array(X), np.array(y)

    def train(self, data: bt.DataBase):
        """训练模型"""
        X, y = self.prepare_training_data(data)

        if len(X) == 0 or len(y) == 0:
            print("训练数据不足")
            return

        # 训练各个模型
        for name, model in self.models.items():
            model.fit(X, y)

        self.is_trained = True
        print(f"AI模型训练完成，使用 {len(X)} 个样本")

    def predict(self, data: bt.DataBase) -> Tuple[int, float]:
        """预测交易信号"""
        if not self.is_trained:
            # 未训练时返回中性信号
            return 0, 0.5

        # 提取当前特征
        features = self.feature_extractor.extract_features(data)
        feature_vector = (
            features.price_features
            + features.volume_features
            + features.technical_features
            + [
                features.market_regime,
                features.volatility_level,
                features.trend_strength,
            ]
        )

        X_pred = np.array([feature_vector])

        # 集成预测
        predictions = []
        probabilities = []

        for model in self.models.values():
            pred = model.predict(X_pred)[0]
            prob = np.max(model.predict_proba(X_pred)[0])
            predictions.append(pred)
            probabilities.append(prob)

        # 投票决定最终预测
        final_prediction = int(np.sign(np.sum(predictions)))
        confidence = np.mean(probabilities)

        return final_prediction, confidence


class AIStrategy(bt.Strategy):
    """
    AI增强交易策略
    结合传统技术分析和机器学习预测
    """

    params = (
        ("training_period", 100),  # 训练期天数
        ("confidence_threshold", 0.6),  # AI置信度阈值
        ("enable_ai", True),  # 是否启用AI
        ("printlog", True),
    )

    def __init__(self):
        super().__init__()

        # AI组件
        self.ai_predictor = EnsemblePredictor()
        self.is_model_trained = False

        # 传统技术指标
        self.sma_fast = bt.indicators.SimpleMovingAverage(self.data, period=10)
        self.sma_slow = bt.indicators.SimpleMovingAverage(self.data, period=30)
        self.rsi = bt.indicators.RSI(self.data, period=14)
        self.bbands = bt.indicators.BollingerBands(self.data, period=20)

        # 状态变量
        self.position_entry_price = 0.0
        self.days_since_training = 0

    def log(self, txt, level="INFO"):
        """日志记录"""
        if self.p.printlog:
            timestamp = self.datetime.datetime().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{timestamp} | {level} | {txt}")

    def next(self):
        """主逻辑循环"""
        # 定期训练AI模型
        if not self.is_model_trained and len(self.data) >= self.p.training_period:
            self._train_ai_model()

        # 生成交易信号
        self._generate_trading_signals()

    def _train_ai_model(self):
        """训练AI模型"""
        try:
            self.log("开始训练AI模型...")
            self.ai_predictor.train(self.data)
            self.is_model_trained = True
            self.log("AI模型训练完成")
        except Exception as e:
            self.log(f"AI模型训练失败: {e}", "WARNING")
            self.is_model_trained = False

    def _generate_trading_signals(self):
        """生成交易信号"""
        current_position = self.getposition(self.data)
        current_price = self.data.close[0]

        # 获取AI预测
        ai_signal = 0
        ai_confidence = 0.0

        if self.p.enable_ai and self.is_model_trained:
            try:
                ai_signal, ai_confidence = self.ai_predictor.predict(self.data)
            except Exception as e:
                self.log(f"AI预测失败: {e}", "WARNING")

        # 获取传统技术信号
        tech_signal = self._get_technical_signal()

        # 信号融合
        combined_signal = self._combine_signals(ai_signal, ai_confidence, tech_signal)

        # 执行交易
        if combined_signal == 1 and current_position.size <= 0:
            # 买入信号
            size = int(self.broker.getcash() * 0.1 / current_price)  # 10%资金
            if size > 0:
                self.buy(size=size)
                self.position_entry_price = current_price
                self.log(
                    f"买入: 价格={current_price:.2f}, AI置信度={ai_confidence:.2f}"
                )

        elif combined_signal == -1 and current_position.size >= 0:
            # 卖出信号
            if current_position.size > 0:
                self.sell(size=current_position.size)
                pnl = (
                    current_price - self.position_entry_price
                ) * current_position.size
                self.log(f"卖出: 价格={current_price:.2f}, 收益={pnl:.2f}")

    def _get_technical_signal(self) -> int:
        """获取传统技术信号"""
        if len(self.data) < 30:
            return 0

        signal = 0

        # 移动平均线信号
        if (
            self.sma_fast[0] > self.sma_slow[0]
            and self.sma_fast[-1] <= self.sma_slow[-1]
        ):
            signal += 1
        elif (
            self.sma_fast[0] < self.sma_slow[0]
            and self.sma_fast[-1] >= self.sma_slow[-1]
        ):
            signal -= 1

        # RSI信号
        if self.rsi[0] < 30:
            signal += 1
        elif self.rsi[0] > 70:
            signal -= 1

        # 布林带信号
        if self.data.close[0] < self.bbands.lines.bot[0]:
            signal += 1
        elif self.data.close[0] > self.bbands.lines.top[0]:
            signal -= 1

        return np.sign(signal)

    def _combine_signals(
        self, ai_signal: int, ai_confidence: float, tech_signal: int
    ) -> int:
        """融合AI和传统技术信号"""
        if not self.p.enable_ai or ai_confidence < self.p.confidence_threshold:
            # AI置信度不足时主要依赖技术分析
            return tech_signal
        else:
            # 高置信度AI信号加权
            if ai_signal == tech_signal:
                return ai_signal  # 信号一致，增强信心
            else:
                # 信号冲突时，根据置信度决定
                if ai_confidence > 0.8:
                    return ai_signal
                else:
                    return tech_signal

    def stop(self):
        """策略结束"""
        self.log("=== AI策略执行完成 ===")
        self.log(f"最终资产: {self.broker.getvalue():.2f}")
        self.log(
            f"总收益率: {(self.broker.getvalue() - self.broker.startingcash) / self.broker.startingcash:.2%}"
        )
