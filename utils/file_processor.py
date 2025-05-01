

import os
from PyPDF2 import PdfReader
import docx # python-docx
from sklearn.feature_extraction.text import TfidfVectorizer
import re # Thư viện Regular Expression để làm sạch text cơ bản
from collections import Counter # Import Counter để đếm điểm

# --- Định nghĩa Danh mục và Từ khóa liên quan ---
# Bạn có thể tùy chỉnh danh sách này theo nhu cầu
# Chuyển hết keyword về chữ thường để dễ so khớp
CATEGORY_KEYWORDS = {
    "Lập trình": ["python", "java", "javascript", "js", "code", "coding", "lap trinh", "html", "css", "web", "flask", "django", "react", "angular", "api", "php", "c++", "c#", "ruby", "swift", "kotlin", "algorithm", "thuat toan"],
    "Khoa học May tinh": ["computer science", "khoa hoc may tinh", "data structure", "cau truc du lieu", "machine learning", "hoc may", "ai", "tri tue nhan tao", "database", "co so du lieu", "sql", "network", "mang may tinh", "operating system", "he dieu hanh", "security", "bao mat", "big data"],
    "Toán học": ["math", "mathematics", "toan", "calculus", "giai tich", "algebra", "dai so", "linear algebra", "dai so tuyen tinh", "probability", "xac suat", "statistics", "thong ke", "geometry", "hinh hoc", "differential equation", "phuong trinh vi phan"],
    "Vật lý": ["physics", "vat ly", "mechanics", "co hoc", "optics", "quang hoc", "thermodynamics", "nhiet dong luc hoc", "electromagnetism", "dien tu", "quantum", "luong tu", "relativity", "tuong doi"],
    "Hóa học": ["chemistry", "hoa hoc", "organic", "huu co", "inorganic", "vo co", "physical chemistry", "hoa ly", "analytical", "phan tich", "biochemistry", "hoa sinh"],
    "Sinh học": ["biology", "sinh hoc", "genetics", "di truyen", "evolution", "tien hoa", "ecology", "sinh thai", "cell", "te bao", "molecular biology", "sinh hoc phan tu"],
    "Ngoại ngữ": ["english", "tieng anh", "ielts", "toefl", "toeic", "grammar", "ngu phap", "vocabulary", "tu vung", "french", "tieng phap", "japanese", "tieng nhat", "chinese", "tieng trung"],
    "Kinh tế": ["economics", "kinh te", "microeconomics", "kinh te vi mo", "macroeconomics", "kinh te vi mo", "finance", "tai chinh", "marketing", "business", "kinh doanh", "investment", "dau tu"],
    "Văn học": ["Tho", "Truyen", "van", "ngu van"],
    # Thêm các danh mục và từ khóa khác nếu cần...
}

DEFAULT_CATEGORY = "Tài liệu chung" # Danh mục mặc định

def extract_text(filepath):
    """
    Trích xuất nội dung văn bản từ file (PDF, DOCX, TXT).
    Args: filepath (str): Đường dẫn đến file.
    Returns: str: Nội dung văn bản, hoặc chuỗi rỗng nếu lỗi.
    """
    _, file_extension = os.path.splitext(filepath)
    text = ""
    try:
        if file_extension.lower() == '.pdf':
            with open(filepath, 'rb') as f:
                reader = PdfReader(f)
                if reader.is_encrypted:
                    try:
                        reader.decrypt('') # Thử mật khẩu rỗng
                    except Exception as decrypt_error:
                        print(f"File PDF {filepath} được mã hóa và không thể giải mã: {decrypt_error}")
                        return ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        elif file_extension.lower() == '.docx':
            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif file_extension.lower() == '.txt':
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read()
            except UnicodeDecodeError:
                 try:
                     with open(filepath, 'r', encoding='latin-1') as f:
                        text = f.read()
                 except Exception as e_alt:
                     print(f"Lỗi khi đọc file TXT {filepath} với UTF-8 và latin-1: {e_alt}")
                     return ""
        else:
            print(f"Định dạng file {file_extension} không được hỗ trợ.")
            return ""

        text = re.sub(r'\s+', ' ', text).strip() # Làm sạch khoảng trắng
        return text

    except Exception as e:
        print(f"Lỗi khi đọc file {filepath}: {e}")
        return ""

def extract_keywords(text, num_keywords=15): # Tăng số keywords mặc định
    """
    Trích xuất từ khóa từ văn bản bằng TF-IDF.
    Args: text (str), num_keywords (int).
    Returns: list: Danh sách từ khóa.
    """
    if not text or not isinstance(text, str) or len(text.split()) < 5:
        print("Nội dung văn bản không đủ để trích xuất từ khóa.")
        return []

    try:
        vectorizer = TfidfVectorizer(stop_words='english', max_df=0.85, ngram_range=(1, 2), max_features=3000)
        tfidf_matrix = vectorizer.fit_transform([text])
        feature_names = vectorizer.get_feature_names_out()
        tfidf_scores = tfidf_matrix[0].T.todense().tolist()
        word_scores = [(score[0], word) for word, score in zip(feature_names, tfidf_scores)]
        word_scores.sort(key=lambda x: x[0], reverse=True)
        keywords = [word for score, word in word_scores[:num_keywords]]
        return keywords

    except Exception as e:
        print(f"Lỗi khi trích xuất từ khóa: {e}")
        return []

def categorize_document(keywords_list):
    """
    Phân loại tài liệu dựa trên danh sách từ khóa.
    Args: keywords_list (list).
    Returns: str: Tên danh mục.
    """
    if not keywords_list:
        return DEFAULT_CATEGORY

    input_keywords_lower = {kw.lower() for kw in keywords_list}
    category_scores = Counter()

    for category, category_kws in CATEGORY_KEYWORDS.items():
        match_count = len(input_keywords_lower.intersection(category_kws))
        if match_count > 0:
            category_scores[category] += match_count

    if category_scores:
        best_category, _ = category_scores.most_common(1)[0]
        return best_category
    else:
        return DEFAULT_CATEGORY