"""XGBoost ML 策略

加载预训练的 XGBoost 模型，通过 predict_proba 获取上涨概率作为评分，
实现 IStrategy 接口，无缝集成到现有策略引擎和回测系统中。

当 XGBoost 不可用时，自动降级为技术指标评分模式。