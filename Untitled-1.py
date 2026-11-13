
class OnlineEvaluationService(Evaluatable):
    def calculate_average(self, evaluations):
        if not evaluations:
            return 0.0
        # 使用列表推导式计算平均分
        scores = [eval.score for eval in evaluations]
        return sum(scores) / len(scores)
