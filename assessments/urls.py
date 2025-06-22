from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

router.register(r'quizzes', views.QuizViewSet)
router.register(r'quiz-questions', views.QuizQuestionViewSet)
router.register(r'quiz-tasks', views.QuizTaskViewSet)
router.register(r'grading-criteria', views.GradingCriterionViewSet)
router.register(r'quiz-submissions', views.QuizSubmissionViewSet)
router.register(r'question-responses', views.QuestionResponseViewSet)
router.register(r'submission-files', views.SubmissionFileViewSet)
router.register(r'quiz-grades', views.QuizGradeViewSet)
router.register(r'task-grades', views.TaskGradeViewSet)
router.register(r'criteria-grades', views.CriteriaGradeViewSet)

urlpatterns = [
    path('', include(router.urls)),
]