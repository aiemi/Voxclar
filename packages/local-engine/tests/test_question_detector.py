"""Tests for LocalQuestionDetector."""
from src.ai.question_detector import LocalQuestionDetector


def test_english_question_mark():
    d = LocalQuestionDetector()
    r = d.detect("What is the time complexity?", "en")
    assert r["is_question"] is True
    assert r["confidence"] > 0.3


def test_english_question_word():
    d = LocalQuestionDetector()
    r = d.detect("How do you handle distributed systems", "en")
    assert r["is_question"] is True


def test_english_aux_verb():
    d = LocalQuestionDetector()
    r = d.detect("Can you explain your experience with databases", "en")
    assert r["is_question"] is True


def test_english_statement():
    d = LocalQuestionDetector()
    r = d.detect("I have five years of experience in Python", "en")
    assert r["is_question"] is False


def test_chinese_question_ending():
    d = LocalQuestionDetector()
    r = d.detect("你能解释一下吗", "zh")
    assert r["is_question"] is True


def test_chinese_question_word():
    d = LocalQuestionDetector()
    r = d.detect("为什么选择这个技术栈", "zh")
    assert r["is_question"] is True


def test_chinese_statement():
    d = LocalQuestionDetector()
    r = d.detect("我有三年的开发经验", "zh")
    assert r["is_question"] is False


def test_behavioral_classification():
    d = LocalQuestionDetector()
    r = d.detect("Tell me about a time when you faced a challenge at work", "en")
    assert r["is_question"] is True
    assert r["question_type"] == "behavioral"


def test_technical_classification():
    d = LocalQuestionDetector()
    r = d.detect("How would you implement a distributed cache", "en")
    assert r["is_question"] is True
    assert r["question_type"] == "technical"


def test_implicit_question():
    d = LocalQuestionDetector()
    r = d.detect("I'm not sure how this works", "en")
    assert r["is_question"] is True


def test_empty_text():
    d = LocalQuestionDetector()
    r = d.detect("", "en")
    assert r["is_question"] is False
