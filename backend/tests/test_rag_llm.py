"""
Unit tests cho app.rag.llm
  - GroqLLM: khởi tạo, gọi API, xử lý lỗi
  - TopicRouter: phân loại query, fallback
"""
import os
import pytest
import requests
from unittest.mock import MagicMock, patch


# ── Fixtures & Helpers ────────────────────────────────────────────────────────

SAMPLE_TOPICS = [
    {"id": 1, "ten": "Hình sự"},
    {"id": 3, "ten": "Hôn nhân và Gia đình"},
    {"id": 5, "ten": "Y tế"},
]


def _fake_groq_resp(content: str, status: int = 200):
    """Tạo mock response giả lập Groq API."""
    resp = MagicMock()
    resp.ok = status < 400
    resp.status_code = status
    resp.text = content
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    if status >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(
            f"HTTP {status}", response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


@pytest.fixture
def groq_llm():
    """GroqLLM instance với API key giả."""
    with patch.dict(os.environ, {"GROQ_API_KEY": "test-key", "LLM_MODEL": "llama3-8b-8192"}):
        from app.rag.llm import GroqLLM
        return GroqLLM()


@pytest.fixture
def mock_llm():
    return MagicMock()


@pytest.fixture
def router(mock_llm):
    from app.rag.llm import TopicRouter
    return TopicRouter(mock_llm, SAMPLE_TOPICS)


# ── GroqLLM.__init__ ──────────────────────────────────────────────────────────

class TestGroqLLMInit:
    def test_raises_without_api_key(self):
        """
        Ngữ cảnh: Không có GROQ_API_KEY trong env lẫn settings.
        Kỳ vọng: GroqLLM() phải raise ValueError với thông báo chứa 'GROQ_API_KEY'.
        Lý do pass: _read_env_key trả về '' (patched) và settings.GROQ_API_KEY=None
                    → self._api_key = '' or None = None → raise ValueError.
        """
        clean_env = {k: v for k, v in os.environ.items() if k != "GROQ_API_KEY"}
        with patch.dict(os.environ, clean_env, clear=True), \
             patch("app.rag.llm._read_env_key", return_value=""), \
             patch("app.rag.llm.settings") as s:
            s.GROQ_API_KEY = None
            s.LLM_MODEL = "llama3-8b-8192"
            from app.rag.llm import GroqLLM
            with pytest.raises(ValueError, match="GROQ_API_KEY"):
                GroqLLM()

    def test_init_stores_api_key(self, groq_llm):
        """
        Ngữ cảnh: GROQ_API_KEY='test-key' trong os.environ.
        Kỳ vọng: groq_llm._api_key == 'test-key'.
        Lý do pass: _read_env_key đọc os.environ trước → trả về 'test-key'.
        """
        assert groq_llm._api_key == "test-key"

    def test_init_sets_groq_url(self, groq_llm):
        """
        Ngữ cảnh: GroqLLM khởi tạo thành công.
        Kỳ vọng: URL endpoint phải trỏ đến 'groq.com'.
        Lý do pass: self._url được hardcode là 'https://api.groq.com/...'.
        """
        assert "groq.com" in groq_llm._url


# ── GroqLLM._call ─────────────────────────────────────────────────────────────

class TestGroqLLMCall:
    def test_returns_response_content(self, groq_llm):
        """
        Ngữ cảnh: requests.post trả về response thành công với content='kết quả'.
        Kỳ vọng: _call() trả về đúng chuỗi content từ response JSON.
        Lý do pass: resp.json()['choices'][0]['message']['content'].strip() == 'kết quả'.
        """
        with patch("requests.post", return_value=_fake_groq_resp("kết quả")):
            assert groq_llm._call("prompt") == "kết quả"

    def test_sends_correct_auth_header(self, groq_llm):
        """
        Ngữ cảnh: groq_llm._api_key = 'test-key'.
        Kỳ vọng: Header Authorization phải là 'Bearer test-key'.
        Lý do pass: _call() build header = {'Authorization': f'Bearer {self._api_key}'}.
        """
        with patch("requests.post", return_value=_fake_groq_resp("ok")) as mock_post:
            groq_llm._call("prompt")
        headers = mock_post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test-key"

    def test_sends_correct_model(self, groq_llm):
        """
        Ngữ cảnh: LLM_MODEL='llama3-8b-8192' từ env.
        Kỳ vọng: Payload JSON phải có 'model' == giá trị được cấu hình.
        Lý do pass: payload['model'] = self._model = 'llama3-8b-8192'.
        """
        with patch("requests.post", return_value=_fake_groq_resp("ok")) as mock_post:
            groq_llm._call("prompt")
        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == groq_llm._model

    def test_passes_custom_temperature_and_max_tokens(self, groq_llm):
        """
        Ngữ cảnh: Gọi _call() với temperature=0.0 và max_tokens=10.
        Kỳ vọng: Các giá trị này phải xuất hiện trong payload gửi đi.
        Lý do pass: _call() đặt payload['temperature'] và payload['max_tokens'] từ tham số.
        """
        with patch("requests.post", return_value=_fake_groq_resp("ok")) as mock_post:
            groq_llm._call("prompt", temperature=0.0, max_tokens=10)
        payload = mock_post.call_args[1]["json"]
        assert payload["temperature"] == 0.0
        assert payload["max_tokens"] == 10

    def test_raises_http_error_on_4xx(self, groq_llm):
        """
        Ngữ cảnh: API trả về HTTP 401 Unauthorized.
        Kỳ vọng: _call() phải raise requests.HTTPError.
        Lý do pass: resp.raise_for_status() được gọi và raise HTTPError vì resp.ok=False.
        """
        with patch("requests.post", return_value=_fake_groq_resp("Unauthorized", status=401)):
            with pytest.raises(requests.HTTPError):
                groq_llm._call("prompt")

    def test_raises_http_error_on_5xx(self, groq_llm):
        """
        Ngữ cảnh: API trả về HTTP 500 Internal Server Error.
        Kỳ vọng: _call() phải raise requests.HTTPError.
        Lý do pass: raise_for_status() raise HTTPError cho mọi status >= 400.
        """
        with patch("requests.post", return_value=_fake_groq_resp("Server Error", status=500)):
            with pytest.raises(requests.HTTPError):
                groq_llm._call("prompt")


# ── GroqLLM.generate ──────────────────────────────────────────────────────────

class TestGroqLLMGenerate:
    def test_returns_answer(self, groq_llm):
        """
        Ngữ cảnh: _call() trả về 'câu trả lời' thành công.
        Kỳ vọng: generate() trả về đúng chuỗi đó.
        Lý do pass: generate() gọi _call() và trả về kết quả nếu không rỗng.
        """
        with patch.object(groq_llm, "_call", return_value="câu trả lời"):
            assert groq_llm.generate("prompt") == "câu trả lời"

    def test_429_returns_friendly_busy_message(self, groq_llm):
        """
        Ngữ cảnh: _call() raise Exception với message chứa '429'.
        Kỳ vọng: generate() trả về chuỗi thân thiện chứa 'bận' thay vì re-raise.
        Lý do pass: generate() bắt exception, kiểm tra '429' in str(e) → trả về thông báo bận.
        """
        with patch.object(groq_llm, "_call", side_effect=Exception("429 Too Many Requests")):
            result = groq_llm.generate("prompt")
        assert "bận" in result.lower()

    def test_empty_response_returns_fallback_message(self, groq_llm):
        """
        Ngữ cảnh: _call() trả về chuỗi rỗng ''.
        Kỳ vọng: generate() không trả về chuỗi rỗng — có fallback message.
        Lý do pass: generate() kiểm tra `result or 'Không thể tạo...'` → dùng fallback.
        """
        with patch.object(groq_llm, "_call", return_value=""):
            result = groq_llm.generate("prompt")
        assert result  # không để trống

    def test_non_429_exception_is_re_raised(self, groq_llm):
        """
        Ngữ cảnh: _call() raise HTTPError (không phải 429).
        Kỳ vọng: generate() re-raise exception đó, không nuốt lỗi.
        Lý do pass: generate() chỉ bắt '429', còn lại đều re-raise.
        """
        with patch.object(groq_llm, "_call", side_effect=requests.HTTPError("500")):
            with pytest.raises(requests.HTTPError):
                groq_llm.generate("prompt")


# ── GroqLLM.rewrite_query ─────────────────────────────────────────────────────

class TestGroqLLMRewriteQuery:
    def test_returns_rewritten_query(self, groq_llm):
        """
        Ngữ cảnh: _call() trả về query đã được viết lại theo thuật ngữ pháp lý.
        Kỳ vọng: rewrite_query() trả về đúng chuỗi từ _call().
        Lý do pass: rewrite_query() format REWRITE_PROMPT rồi gọi _call(temperature=0.1).
        """
        with patch.object(groq_llm, "_call", return_value="quy định ly hôn pháp luật"):
            result = groq_llm.rewrite_query("vợ chồng chia tay thì sao?")
        assert result == "quy định ly hôn pháp luật"

    def test_fallback_to_original_on_exception(self, groq_llm):
        """
        Ngữ cảnh: _call() raise Exception (lỗi mạng, timeout...).
        Kỳ vọng: rewrite_query() trả về query gốc, không crash.
        Lý do pass: rewrite_query() bọc _call() trong try/except → fallback về query gốc.
        """
        original = "câu hỏi gốc không thay đổi"
        with patch.object(groq_llm, "_call", side_effect=Exception("lỗi mạng")):
            result = groq_llm.rewrite_query(original)
        assert result == original

    def test_fallback_to_original_on_empty_response(self, groq_llm):
        """
        Ngữ cảnh: _call() trả về chuỗi rỗng.
        Kỳ vọng: rewrite_query() trả về query gốc thay vì chuỗi rỗng.
        Lý do pass: `return self._call(...) or query` → '' or query = query.
        """
        original = "câu hỏi gốc"
        with patch.object(groq_llm, "_call", return_value=""):
            result = groq_llm.rewrite_query(original)
        assert result == original


# ── TopicRouter.__init__ ──────────────────────────────────────────────────────

class TestTopicRouterInit:
    def test_topic_map_built_correctly(self, router):
        """
        Ngữ cảnh: TopicRouter nhận 3 topics: id=1,3,5.
        Kỳ vọng: _topic_map = {'1': 'Hình sự', '3': 'Hôn nhân và Gia đình', '5': 'Y tế'}.
        Lý do pass: __init__ chuyển id thành str key để so sánh với output LLM (luôn là string).
        """
        assert router._topic_map == {
            "1": "Hình sự",
            "3": "Hôn nhân và Gia đình",
            "5": "Y tế",
        }

    def test_topic_list_string_contains_all_names(self, router):
        """
        Ngữ cảnh: TopicRouter khởi tạo với 3 topics.
        Kỳ vọng: _topic_list_str chứa tên tất cả các topic (dùng trong prompt gửi LLM).
        Lý do pass: __init__ join các topic thành string bằng '\\n'.
        """
        assert "Hình sự" in router._topic_list_str
        assert "Y tế" in router._topic_list_str

    def test_empty_topics_creates_empty_map(self, mock_llm):
        """
        Ngữ cảnh: TopicRouter nhận list topics rỗng [].
        Kỳ vọng: _topic_map = {} → route() sẽ luôn trả về None.
        Lý do pass: dict comprehension trên list rỗng → {}.
        """
        from app.rag.llm import TopicRouter
        r = TopicRouter(mock_llm, [])
        assert r._topic_map == {}


# ── TopicRouter.route ─────────────────────────────────────────────────────────

class TestTopicRouterRoute:
    def test_returns_valid_topic_id(self, router, mock_llm):
        """
        Ngữ cảnh: LLM trả về '3' — ID hợp lệ trong topic_map.
        Kỳ vọng: route() trả về '3' (chu_de_id để filter ChromaDB).
        Lý do pass: re.search tìm thấy '3', '3' in _topic_map → return '3'.
        """
        mock_llm._call.return_value = "3"
        assert router.route("điều kiện kết hôn là gì?") == "3"

    def test_returns_none_when_llm_returns_zero(self, router, mock_llm):
        """
        Ngữ cảnh: LLM trả về '0' — quy ước 'không khớp chủ đề nào'.
        Kỳ vọng: route() trả về None → RAGPipeline sẽ tìm kiếm toàn bộ corpus.
        Lý do pass: '0' được kiểm tra riêng trước khi lookup topic_map → return None.
        """
        mock_llm._call.return_value = "0"
        assert router.route("câu hỏi không liên quan pháp luật") is None

    def test_returns_none_for_unknown_id(self, router, mock_llm):
        """
        Ngữ cảnh: LLM ảo tưởng trả về '99' — ID không tồn tại trong DB.
        Kỳ vọng: route() trả về None thay vì crash.
        Lý do pass: '99' not in _topic_map → không vào nhánh return → fall through → None.
        """
        mock_llm._call.return_value = "99"
        assert router.route("bất kỳ") is None

    def test_returns_none_when_no_integer_in_response(self, router, mock_llm):
        """
        Ngữ cảnh: LLM trả về text thuần 'không biết' không có số.
        Kỳ vọng: route() trả về None thay vì crash khi parse.
        Lý do pass: re.search(r'\\d+', 'không biết') trả về None → return None sớm.
        """
        mock_llm._call.return_value = "không biết"
        assert router.route("query") is None

    def test_returns_none_on_llm_exception(self, router, mock_llm):
        """
        Ngữ cảnh: LLM raise exception (timeout, 429...).
        Kỳ vọng: route() bắt exception và trả về None — không crash pipeline.
        Lý do pass: try/except trong route() bắt mọi Exception → return None.
        """
        mock_llm._call.side_effect = Exception("LLM lỗi")
        assert router.route("query") is None

    def test_returns_none_when_topics_empty(self, mock_llm):
        """
        Ngữ cảnh: TopicRouter khởi tạo với topics rỗng.
        Kỳ vọng: route() trả về None ngay lập tức, không gọi LLM.
        Lý do pass: `if not self._topic_map: return None` — guard clause đầu hàm.
        """
        from app.rag.llm import TopicRouter
        empty_router = TopicRouter(mock_llm, [])
        assert empty_router.route("bất kỳ") is None
        mock_llm._call.assert_not_called()

    def test_extracts_id_from_noisy_response(self, router, mock_llm):
        """
        Ngữ cảnh: LLM trả về 'ID: 5.' thay vì chỉ '5' (LLM hay thêm prefix).
        Kỳ vọng: route() vẫn extract được '5' và trả về đúng.
        Lý do pass: re.search(r'\\d+', 'ID: 5.') tìm thấy '5' — robust hơn split().
        """
        mock_llm._call.return_value = "ID: 5."
        assert router.route("vấn đề y tế") == "5"

    def test_extracts_first_id_from_multiline_response(self, router, mock_llm):
        """
        Ngữ cảnh: LLM trả về nhiều dòng '1\\n3' — lấy số đầu tiên.
        Kỳ vọng: route() trả về '1', không trả về '3'.
        Lý do pass: re.search() tìm match đầu tiên trong string → '1'.
        """
        mock_llm._call.return_value = "1\n3"
        assert router.route("hình sự") == "1"

    def test_calls_llm_with_correct_temperature(self, router, mock_llm):
        """
        Ngữ cảnh: route() gọi LLM để phân loại topic.
        Kỳ vọng: temperature=0.0 để output deterministic (classification task).
        Lý do pass: route() gọi self.llm._call(prompt, temperature=0.0, ...).
        """
        mock_llm._call.return_value = "0"
        router.route("query")
        _, call_kwargs = mock_llm._call.call_args
        assert call_kwargs.get("temperature") == 0.0

    def test_calls_llm_with_small_max_tokens(self, router, mock_llm):
        """
        Ngữ cảnh: route() chỉ cần LLM trả về 1 con số (rất ngắn).
        Kỳ vọng: max_tokens <= 10 để tiết kiệm token và tăng tốc.
        Lý do pass: route() gọi _call(..., max_tokens=10).
        """
        mock_llm._call.return_value = "0"
        router.route("query")
        _, call_kwargs = mock_llm._call.call_args
        assert call_kwargs.get("max_tokens") <= 10
