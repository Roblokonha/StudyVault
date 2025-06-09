# app.py
# -*- coding: utf-8 -*-

import os
import traceback
import random
import re
import docx  # Thư viện đọc file .docx
import fitz  # Thư viện PyMuPDF để đọc file .pdf
from datetime import datetime, date, timedelta, timezone
from flask import (Flask, render_template, request, redirect, url_for, flash,
                   send_from_directory, abort, jsonify)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_, desc
from sqlalchemy import func as sql_func
from sqlalchemy.exc import SQLAlchemyError

# --- MockFileProcessor và Khởi tạo App ---
class FileProcessor:
    DEFAULT_CATEGORY = "Chưa phân loại"
    CATEGORY_KEYWORDS = {
        "Lập trình": ["python", "java", "code", "script", "lập trình", "thuật toán", "hàm", "biến", "vòng lặp"],
        "Kinh tế học": ["kinh tế", "thị trường", "gdp", "lạm phát", "cung", "cầu", "vi mô", "vĩ mô"],
        "Toán học": ["toán", "công thức", "phương trình", "tích phân", "đạo hàm", "ma trận", "vector"],
        "Ngoại ngữ": ["english", "tiếng anh", "từ vựng", "grammar", "ielts", "toeic"],
        "Kỹ năng mềm": ["cv", "giao tiếp", "thuyết trình", "lãnh đạo"],
        "Pháp luật": ["luật", "hiến pháp", "điều khoản", "nghị định", "thông tư"],
        "AI/ML": ["machine learning", "ai", "neural network", "mạng nơ-ron", "học máy"],
        "Link Web": ["http", "https"],
        "Hình ảnh": ["image", "picture"],
        "Video": ["video", "media"],
        "Google Drive": ["google drive", "gsheet"]
    }

    def extract_text(self, filepath):
        """
        Trích xuất nội dung văn bản từ các loại file khác nhau (pdf, docx, txt).
        """
        try:
            ext = os.path.splitext(filepath)[1].lower()
            if ext == '.pdf':
                with fitz.open(filepath) as doc:
                    text = "".join(page.get_text() for page in doc)
                return text
            elif ext == '.docx':
                doc = docx.Document(filepath)
                return "\n".join([para.text for para in doc.paragraphs])
            elif ext == '.txt':
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return f"[Lỗi: Định dạng file '{ext}' không được hỗ trợ để trích xuất văn bản.]"
        except Exception as e:
            print(f"ERROR extracting text from {filepath}: {e}")
            return f"[Lỗi: Không thể đọc nội dung từ file. File có thể bị hỏng hoặc cần quyền truy cập. Chi tiết: {e}]"

    def categorize_document(self, keywords):
        for cat, keys in self.CATEGORY_KEYWORDS.items():
            keyword_string = ' '.join(keywords).lower() if isinstance(keywords, list) else (keywords or '').lower()
            if any(k in keyword_string for k in keys):
                return cat
        return self.DEFAULT_CATEGORY
    
    def build_objectives_tree(items):
        tree = []
        # Khởi tạo map với tất cả các item
        item_map = {item.id: {
            "id": item.id,
            "description": item.description,
            "is_completed": item.is_completed,
            "sub_objectives": []
        } for item in items}

        # Xây dựng cấu trúc cây
        for item in items:
            # Chắc chắn rằng biến được sử dụng là "item", không phải "itemm"
            if item.parent_id is not None and item.parent_id in item_map:
                # Nếu có cha, thêm item hiện tại vào danh sách con của cha
                parent_item_data = item_map[item.parent_id]
                parent_item_data["sub_objectives"].append(item_map[item.id])
            else:
                # Nếu không có cha, đây là item cấp cao nhất
                tree.append(item_map[item.id])
        
        return tree


app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads/')
app.config['SECRET_KEY'] = 'dev_secret_key_should_be_changed'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'studyvault.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'docx'}
app.config['ALLOWED_IMAGE_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['ALLOWED_VIDEO_EXTENSIONS'] = {'mp4', 'mov', 'avi', 'mkv'}
db = SQLAlchemy(app)
migrate = Migrate(app, db)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
ITEMS_PER_PAGE = 10

fp = FileProcessor()

# --- Model Dữ liệu ---
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(300), nullable=False, unique=True)
    category = db.Column(db.String(100), nullable=True, default=fp.DEFAULT_CATEGORY)
    uploaded_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_viewed_date = db.Column(db.DateTime, nullable=True)
    doc_type = db.Column(db.String(20), nullable=False, default='file')
    engagement_level = db.Column(db.String(50), nullable=True)
    custom_note = db.Column(db.Text, nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    extracted_content = db.Column(db.Text, nullable=True)
    workspace_items = db.relationship('WorkspaceItem', 
                                      primaryjoin="and_(Document.id==WorkspaceItem.document_id, WorkspaceItem.parent_id==None)",
                                      backref='document', 
                                      lazy=True, 
                                      cascade="all, delete-orphan")
    win_criteria_description = db.Column(db.Text, nullable=True)
    target_score = db.Column(db.Integer, nullable=True)
    actual_score = db.Column(db.Integer, nullable=True)
    keywords = db.Column(db.Text, nullable=True) 
    context_event = db.Column(db.String(200), nullable=True) # <-- THÊM DÒNG NÀY
    learning_objectives = db.relationship('LearningObjective', primaryjoin="and_(Document.id==LearningObjective.document_id, LearningObjective.parent_id==None)", backref='doc', lazy=True, cascade="all, delete-orphan")
    


class WorkspaceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, nullable=True)
    order = db.Column(db.Integer, nullable=False, default=0)
    user_content = db.Column(db.Text, nullable=True)
    
    # --- CÁC THAY ĐỔI QUAN TRỌNG ---
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
    
    # Trường này sẽ lưu ID của item cha. Nếu là NULL, nó là item cấp cao nhất.
    parent_id = db.Column(db.Integer, db.ForeignKey('workspace_item.id'), nullable=True)

    # Mối quan hệ tự tham chiếu để lấy các item con
    children = db.relationship('WorkspaceItem',
        backref=db.backref('parent', remote_side=[id]),
        lazy=True,
        cascade="all, delete-orphan"
    )

class LearningObjective(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500), nullable=False)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('learning_objective.id'), nullable=True)

    sub_objectives = db.relationship('LearningObjective',
        backref=db.backref('parent', remote_side=[id]),
        lazy=True,
        cascade="all, delete-orphan"
    )
    
    # --- CÁC TRƯỜNG NHÃN MỚI ---
    importance = db.Column(db.String(50), nullable=True)      # core, supporting, advanced
    learning_role = db.Column(db.String(50), nullable=True)   # concept, tool, example
    difficulty = db.Column(db.String(50), nullable=True)      # easy, medium, hard

    def __repr__(self):
        return f'<SubItem {self.id}: {self.title}>'
    


# --- Helper Functions ---
def normalize_vietnamese(text):
    if not text: return ""
    replacements = {'á': 'a', 'à': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a','ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a','â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a','đ': 'd','é': 'e', 'è': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e','ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e','í': 'i', 'ì': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i','ó': 'o', 'ò': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o','ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o','ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o','ú': 'u', 'ù': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u','ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u','ý': 'y', 'ỳ': 'y', 'ỷ': 'y', 'ĩ': 'y', 'ỵ': 'y',}
    text_lower = text.lower()
    return "".join([replacements.get(char, char) for char in text_lower])

def get_random_docs(model, num_docs):
    all_ids = db.session.query(model.id).all()
    if not all_ids: return []
    random_id_tuples = random.sample(all_ids, min(len(all_ids), num_docs))
    random_ids = [r[0] for r in random_id_tuples]
    return model.query.filter(model.id.in_(random_ids)).all()

def allowed_file(filename): return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
def allowed_image(filename): return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_IMAGE_EXTENSIONS']
def allowed_video(filename): return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_VIDEO_EXTENSIONS']
def is_google_drive_link(url): return url and "drive.google.com" in url.lower()
def get_unique_random_elements(input_list, num_elements):
    if not input_list: return []
    return random.sample(input_list, min(len(input_list), num_elements))
STOP_WORDS = set(["là", "và", "của", "có", "trong", "để", "một", "không", "được", "cho", "với", "tại","thì", "mà", "khi", "từ", "ra", "lên", "xuống", "vào", "qua", "đến", "đi", "lại","như", "ở", "đã", "sẽ", "đang", "rằng", "hay", "hơn", "rất", "này", "đó", "kia", "ấy","tôi", "bạn", "anh", "chị", "em", "ông", "bà", "nó", "chúng", "mình","the", "a", "an", "is", "are", "was", "were", "of", "in", "on", "at", "to", "for","with", "by", "from", "as", "and", "or", "but", "if", "then", "this", "that", "it","its", "i", "you", "he", "she", "we", "they", "my", "your", "his", "her", "our", "their"])
def create_fill_in_the_blank_question(content_text, num_blanks=1, min_word_len=4):
    if not content_text or not isinstance(content_text, str): return None
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', content_text)
    potential_sentences = [s.strip() for s in sentences if len(s.strip().split()) > 5]
    if not potential_sentences: return None
    random.shuffle(potential_sentences)
    for sentence in potential_sentences:
        words = re.findall(r'\b\w+\b', sentence.lower())
        candidate_keywords = [word for word in words if len(word) >= min_word_len and word not in STOP_WORDS]
        if len(candidate_keywords) < num_blanks: continue
        words_to_blank = random.sample(candidate_keywords, num_blanks)
        original_sentence = sentence; question_sentence = sentence
        original_words_for_answer = []
        words_to_blank.sort(key=len, reverse=True)
        for word_to_blank_lower in words_to_blank:
            match = re.search(r'\b' + re.escape(word_to_blank_lower) + r'\b', question_sentence, re.IGNORECASE)
            if match:
                original_word = match.group(0)
                new_question_sentence = re.sub(r'\b' + re.escape(original_word) + r'\b', "______", question_sentence, 1, flags=re.IGNORECASE)
                if new_question_sentence != question_sentence:
                    question_sentence = new_question_sentence
                    original_words_for_answer.append(original_word)
        if len(original_words_for_answer) == num_blanks:
            return {"q": question_sentence, "a": " / ".join(original_words_for_answer), "original_sentence": original_sentence}
    return None

def build_tree(items):
    tree = []
    # Tạo một map để truy cập nhanh các item bằng ID
    item_map = {item.id: {
        "id": item.id,
        "title": item.title,
        "content": item.content,
        "order": item.order,
        "user_content": item.user_content,
        # Thêm các trường khác nếu cần
        "children": []
    } for item in items}

    for item in items:
        if item.parent_id is not None and item.parent_id in item_map:
            # Nếu có cha, thêm nó vào danh sách con của cha
            parent_item = item_map[item.parent_id]
            parent_item["children"].append(item_map[item.id])
        else:
            # Nếu không có cha, nó là item cấp cao nhất
            tree.append(item_map[item.id])
            
    # Sắp xếp lại các cây con theo thứ tự
    for item_data in item_map.values():
        item_data['children'].sort(key=lambda x: x['order'])
    
    # Sắp xếp các mục cấp cao nhất
    tree.sort(key=lambda x: x['order'])
    return tree

def build_objectives_tree(items):
    tree = []
    item_map = {item.id: {
        "id": item.id,
        "description": item.description,
        "is_completed": item.is_completed,
        "sub_objectives": []
    } for item in items}

    for item in items:
        if item.parent_id is not None and item.parent_id in item_map:
            parent_item = item_map[item.parent_id]
            parent_item["sub_objectives"].append(item_map[item.id])
        else:
            tree.append(item_map[item.id])

    return tree

# --- Routes ---
@app.route('/')
def index():
    pagination_data = None; documents_on_page = []; suggested_docs = []
    search_query = request.args.get('search_query', '').strip()
    category_filter = request.args.get('category', '').strip()
    available_categories = sorted(list(fp.CATEGORY_KEYWORDS.keys()))
    if fp.DEFAULT_CATEGORY not in available_categories: available_categories.append(fp.DEFAULT_CATEGORY); available_categories.sort()

    try:
        page = request.args.get('page', 1, type=int)
        query = Document.query
        if search_query: query = query.filter(or_(Document.filename.ilike(f"%{search_query}%"), Document.keywords.ilike(f"%{search_query}%")))
        if category_filter: query = query.filter(Document.category == category_filter)
        query = query.order_by(Document.uploaded_date.desc())
        pagination_data = query.paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
        documents_on_page = pagination_data.items if pagination_data else []
        try:
            suggested_docs_ids = db.session.query(Document.id).filter(or_(Document.last_viewed_date.is_(None), Document.engagement_level.is_(None), Document.context_event.is_(None))).limit(20).all()
            if suggested_docs_ids:
                random_id_tuples = random.sample(suggested_docs_ids, min(len(suggested_docs_ids), 3))
                random_ids = [r[0] for r in random_id_tuples]
                suggested_docs = Document.query.filter(Document.id.in_(random_ids)).all()
        except Exception as suggest_err: print(f"WARNING: Cannot get suggested docs: {suggest_err}")
    except Exception as db_err:
        flash(f"Lỗi khi truy vấn dữ liệu: {db_err}", "danger"); print(f"ERROR querying database: {db_err}"); traceback.print_exc()
    try:
        return render_template('index.html', pagination=pagination_data, documents=documents_on_page, categories=available_categories, search_query=search_query, category_filter=category_filter, default_category=fp.DEFAULT_CATEGORY, suggested_docs=suggested_docs )
    except Exception as render_err:
        flash(f"Lỗi nghiêm trọng khi hiển thị trang: {render_err}", "danger"); print(f"ERROR rendering template: {render_err}"); traceback.print_exc()
        return "Đã xảy ra lỗi nghiêm trọng khi tải trang.", 500

@app.route('/document/<int:doc_id>/workspace', methods=['GET'])
def get_workspace_data(doc_id):
    """
    API để lấy toàn bộ cấu trúc workspace đa cấp của một tài liệu.
    """
    doc = db.session.get(Document, doc_id)
    if not doc:
        return jsonify({"error": "Tài liệu không tồn tại."}), 404

    try:
        all_items = WorkspaceItem.query.filter_by(document_id=doc_id).order_by(WorkspaceItem.order).all()
        workspace_tree = build_tree(all_items)
        return jsonify(workspace_tree)

    except Exception as e:
        print(f"ERROR in get_workspace_data for doc {doc_id}: {e}")
        traceback.print_exc()
        return jsonify({"error": "Lỗi server khi lấy dữ liệu workspace."}), 500

# API MỚI ĐỂ TẠO MỘT WORKSPACE ITEM (CÓ THỂ LÀ CHA HOẶC CON)
@app.route('/document/<int:doc_id>/workspace_items', methods=['POST'])
def create_workspace_item(doc_id):
    doc = db.session.get(Document, doc_id)
    if not doc:
        return jsonify({"error": "Tài liệu không tồn tại."}), 404

    data = request.get_json()
    title = data.get('title', '').strip()
    if not title:
        return jsonify({"error": "Tiêu đề không được để trống."}), 400

    content = data.get('content', '')
    parent_id = data.get('parent_id')

    try:
        if parent_id:
            max_order = db.session.query(sql_func.max(WorkspaceItem.order)).filter_by(parent_id=parent_id).scalar() or 0
        else:
            max_order = db.session.query(sql_func.max(WorkspaceItem.order)).filter_by(document_id=doc_id, parent_id=None).scalar() or 0

        new_item = WorkspaceItem(
            title=title, content=content, order=max_order + 1,
            document_id=doc_id, parent_id=parent_id if parent_id else None
        )
        db.session.add(new_item)
        db.session.commit()

        return jsonify({ "id": new_item.id, "title": new_item.title, "content": new_item.content, "order": new_item.order, "parent_id": new_item.parent_id, "children": [] }), 201

    except Exception as e:
        db.session.rollback()
        print(f"ERROR creating workspace_item for doc {doc_id}: {e}")
        return jsonify({"error": "Lỗi server khi tạo mục."}), 500
    
@app.route('/workspace_item/<int:item_id>/user_content', methods=['POST'])
def save_workspace_item_user_content(item_id):
    item = db.session.get(WorkspaceItem, item_id)
    if not item:
        return jsonify({"error": "Mục không tồn tại."}), 404

    data = request.get_json()
    user_content = data.get('user_content', '')

    try:
        item.user_content = user_content
        db.session.commit()

        # Logic giả lập AI tạo câu hỏi
        questions = []
        user_content_lower = user_content.lower()

        if 'điện trường' in user_content_lower:
            questions.extend([
                {"id": 1, "q": "Điện trường là gì và tính chất cơ bản nhất của nó là gì?", "type": "Định nghĩa"},
                {"id": 2, "q": "Vector cường độ điện trường tại một điểm được định nghĩa như thế nào? Nêu đặc điểm (điểm đặt, phương, chiều, độ lớn).", "type": "Khái niệm"},
                {"id": 3, "q": "Phân biệt điện trường do điện tích điểm Q dương và điện tích điểm Q âm gây ra.", "type": "So sánh"}
            ])
        elif 'công thức' in user_content_lower and 'e =' in user_content_lower:
            questions.append({"id": 4, "q": "Áp dụng công thức E = k|q|/r² để tính E tại một điểm M cách q=5nC một khoảng 10cm.", "type": "Vận dụng"})
        
        # Fallback message if no keywords are matched
        if not questions:
            questions.append({"id": 0, "q": "Nội dung chưa đủ để tạo câu hỏi, hãy thử phân tích sâu hơn về một khái niệm cụ thể.", "type": "Gợi ý"})

        return jsonify({"message": "Lưu thành công!", "questions": questions})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Lỗi server khi lưu nội dung."}), 500
        
@app.route('/workspace_item/<int:item_id>/ai_suggestion', methods=['POST'])
def get_ai_suggestion(item_id):
    if not db.session.get(WorkspaceItem, item_id):
        return jsonify({"error": "Mục không tồn tại."}), 404
        
    data = request.get_json()
    user_content = data.get('user_content', '').lower()

    suggestion = ""
    if 'điện trường' in user_content:
        suggestion = (
            "Thử giải thích bằng một phép so sánh đơn giản xem sao nhé! "
            "Ví dụ: 'Hãy tưởng tượng bạn đứng gần một cái lò sưởi, dù không chạm vào nhưng vẫn thấy ấm. Cái ấm đó lan ra từ lò - giống như điện trường lan ra từ một vật mang điện. "
            "Khi bạn đặt một vật mang điện (như cực pin) ở đâu đó, xung quanh nó sẽ xuất hiện một vùng vô hình. Nếu đặt một vật khác cũng có điện vào vùng đó, nó sẽ bị hút hoặc đẩy. Vùng vô hình ấy chính là điện trường.'"
        )
    elif 'tĩnh điện' in user_content or 'lực điện' in user_content:
        suggestion = (
            "Bạn có thể dùng câu chuyện về chiếc bóng bay để giải thích! "
            "Ví dụ: 'Khi bạn chà xát một quả bóng bay vào tóc, những hạt bụi nhỏ li ti từ tóc sẽ dính sang bóng và ngược lại. "
            "Những hạt bụi này có khả năng hút hoặc đẩy nhau. Nếu chúng &quot;thích&quot; nhau, chúng sẽ kéo lại gần; nếu &quot;ghét&quot; nhau, chúng sẽ đẩy nhau ra. "
            "Kết luận: Hạt bụi có khả năng hút đẩy nhau gọi là <b>điện tích</b>. &quot;Tình cảm&quot; giữa các hạt bụi (hút hoặc đẩy) chính là <b>lực điện</b>.'"
        )
    else:
        generic_suggestions = [
            "Bạn có thể diễn giải lại một cách đơn giản hơn được không?",
            "Thử mở rộng thêm lý thuyết liên quan xem sao.",
            "Hãy thử liên kết khái niệm này với một ví dụ trong thực tế."
        ]
        suggestion = random.choice(generic_suggestions)

    return jsonify({"suggestion": suggestion})

    
@app.route('/workspace_item/<int:item_id>/labels', methods=['PUT'])
def update_workspace_item_labels(item_id):
    item = db.session.get(WorkspaceItem, item_id)
    if not item:
        return jsonify({"error": "Mục không tồn tại."}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Dữ liệu không hợp lệ."}), 400

    try:
        item.importance = data.get('importance', item.importance)
        item.learning_role = data.get('learning_role', item.learning_role)
        item.difficulty = data.get('difficulty', item.difficulty)
        db.session.commit()

        return jsonify({
            "id": item.id,
            "title": item.title,
            "importance": item.importance,
            "learning_role": item.learning_role,
            "difficulty": item.difficulty
        })

    except Exception as e:
        db.session.rollback()
        print(f"ERROR updating labels for item {item_id}: {e}")
        return jsonify({"error": "Lỗi server khi cập nhật nhãn."}), 500


# --- API TẠO MỤC CON MỚI ---

    
@app.route('/upload', methods=['GET', 'POST'], endpoint='upload_file')
def upload_file_route():
    if request.method == 'POST':
        upload_type = request.form.get('upload_type')
        filename = None
        filepath = None
        doc_to_save = None
        category = None  # Khởi tạo biến category

        learning_goal_form = request.form.get('learning_goal', '').strip()
        deadline_str = request.form.get('deadline', '').strip()
        deadline_date = None
        if deadline_str:
            try:
                deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Định dạng ngày không hợp lệ.', 'warning')

        try:
            if upload_type == 'file':
                file_key = 'document_file'
                if file_key not in request.files: raise ValueError('Không có file được chọn')
                file = request.files[file_key]
                if file.filename == '': raise ValueError('Chưa chọn file nào')
                if not allowed_file(file.filename): raise ValueError('Định dạng file không hợp lệ (cần PDF, DOCX, TXT).')
                
                filename = secure_filename(file.filename)
                filepath = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                if Document.query.filter_by(filepath=filepath).first(): raise ValueError(f'File "{filename}" đã tồn tại.')
                
                file.save(filepath)
                # Tự động phân loại dựa trên nội dung (giả lập) hoặc từ khóa tên file
                category = fp.categorize_document(filename)
                doc_to_save = Document(filename=filename, filepath=filepath, doc_type=filename.rsplit('.', 1)[1].lower(), category=category)

            elif upload_type == 'image':
                file_key = 'document_image'
                if file_key not in request.files: raise ValueError('Không có file ảnh được chọn')
                file = request.files[file_key]
                if file.filename == '': raise ValueError('Chưa chọn file ảnh nào')
                if not allowed_image(file.filename): raise ValueError('Định dạng ảnh không hợp lệ.')

                filename = secure_filename(file.filename)
                filepath = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                if Document.query.filter_by(filepath=filepath).first(): raise ValueError(f'Ảnh "{filename}" đã tồn tại.')
                
                file.save(filepath)
                category = "Hình ảnh"
                doc_to_save = Document(filename=filename, filepath=filepath, doc_type='image', category=category)

            elif upload_type == 'video':
                file_key = 'document_video'
                if file_key not in request.files: raise ValueError('Không có file video được chọn')
                file = request.files[file_key]
                if file.filename == '': raise ValueError('Chưa chọn file video nào')
                if not allowed_video(file.filename): raise ValueError('Định dạng video không hợp lệ.')

                filename = secure_filename(file.filename)
                filepath = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                if Document.query.filter_by(filepath=filepath).first(): raise ValueError(f'Video "{filename}" đã tồn tại.')

                file.save(filepath)
                category = "Video"
                doc_to_save = Document(filename=filename, filepath=filepath, doc_type='video', category=category)

            elif upload_type in ['link', 'googledrive_link']:
                url_key = 'document_url' if upload_type == 'link' else 'document_gdrive_link'
                doc_url = request.form.get(url_key)
                if not doc_url: raise ValueError('Chưa nhập URL')
                if is_google_drive_link(doc_url) and upload_type == 'link': raise ValueError('Vui lòng dùng mục "Link Google Drive" cho link này.')
                if Document.query.filter_by(filepath=doc_url).first(): raise ValueError(f'Link "{doc_url}" đã tồn tại.')
                
                category = "Google Drive" if upload_type == 'googledrive_link' else "Link Web"
                doc_to_save = Document(filename=doc_url, filepath=doc_url, category=category, doc_type=upload_type)
            
            else:
                raise ValueError('Loại upload không hợp lệ.')

            if doc_to_save:
                # Gán các trường chung
                doc_to_save.learning_goal = learning_goal_form if learning_goal_form else None
                doc_to_save.deadline = deadline_date
                
                # Backfill normalized name
                doc_to_save.filename_normalized = normalize_vietnamese(doc_to_save.filename)
                
                db.session.add(doc_to_save)
                db.session.commit()
                flash(f'Đã lưu "{doc_to_save.filename}".', 'success')
                return redirect(url_for('view_document', document_id=doc_to_save.id, new_upload='true'))

        except ValueError as ve:
            flash(str(ve), 'warning')
            return redirect(request.url)
        except Exception as e:
            flash(f'Lỗi không xác định khi upload: {e}', 'danger')
            traceback.print_exc()
            return redirect(request.url)

    return render_template('upload.html')

@app.route('/document/<int:document_id>', methods=['GET', 'POST'])
def view_document(document_id):
    doc = db.session.get(Document, document_id)
    if not doc: abort(404)
    if request.method == 'POST':
        form_marker = request.form.get('form_marker')
        try:
            if form_marker == 'update_context':
                # Lấy dữ liệu từ form
                doc.engagement_level = request.form.get('engagement_level')
                doc.context_event = request.form.get('context_event')
                doc.custom_note = request.form.get('custom_note')
                
                # Bổ sung lại logic xử lý 'learning_goal' và 'deadline'
                doc.learning_goal = request.form.get('learning_goal', '').strip() or None
                deadline_str = request.form.get('deadline', '').strip()
                if deadline_str:
                    try:
                        doc.deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
                    except ValueError:
                        flash('Định dạng ngày cho thời hạn không hợp lệ.', 'warning')
                else:
                    doc.deadline = None
                    
                db.session.commit()
                flash('Đã cập nhật thông tin ngữ cảnh.', 'success')
            elif form_marker == 'submit_summary':
                user_summary = request.form.get('user_summary', '').strip()
                if user_summary:
                    doc.user_summary = user_summary
                    doc.ai_topic_label = fp.categorize_document([user_summary])
                    db.session.commit()
                    flash(f'Đã lưu tóm tắt của bạn. AI gợi ý: {doc.ai_topic_label}', 'info')
                else: flash('Bạn chưa nhập tóm tắt.', 'warning')
            else: flash('Yêu cầu không hợp lệ.', 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi xử lý yêu cầu: {e}', 'danger')
        return redirect(url_for('view_document', document_id=document_id))
            
    physical_filepath_to_check = None
    if doc.doc_type not in ['link', 'googledrive_link']:
        try:
            upload_dir = os.path.abspath(app.config['UPLOAD_FOLDER'])
            potential_paths = [os.path.join(upload_dir, secure_filename(doc.filename)), os.path.join(upload_dir, doc.filename)]
            for path in potential_paths:
                if os.path.exists(path): physical_filepath_to_check = path; break
        except Exception as e: print(f"ERROR constructing file path: {e}")
            
    try:
        doc.last_viewed_date = datetime.now(timezone.utc)
        if doc.doc_type in ['pdf', 'docx', 'txt', 'file'] and not doc.extracted_content and physical_filepath_to_check:
            temp_content = fp.extract_text(physical_filepath_to_check)
            doc.extracted_content = temp_content if temp_content and "[Lỗi" not in temp_content else "[File trống hoặc không có nội dung văn bản]"
        db.session.commit()
    except Exception as e: db.session.rollback(); print(f"ERROR updating doc on view: {e}")

    extracted_text_content_for_view = None
    if doc.extracted_content and "[Lỗi" not in doc.extracted_content:
        # Tự động định dạng lại văn bản để dễ đọc hơn
        # Nếu văn bản không có ký tự xuống dòng, chúng ta sẽ thêm vào
        if '\n' not in doc.extracted_content:
            temp_text = doc.extracted_content
            # Thêm 2 lần xuống dòng sau mỗi dấu hai chấm (thường là đầu mục)
            temp_text = re.sub(r':\s*', ':\n\n', temp_text)
            # Thêm xuống dòng sau mỗi dấu chấm câu
            temp_text = re.sub(r'([.?!])\s+', r'\1\n', temp_text)
            extracted_text_content_for_view = temp_text
        else:
            # Nếu văn bản đã có sẵn định dạng thì giữ nguyên
            extracted_text_content_for_view = doc.extracted_content
    
    related_docs = []
    if doc.category and doc.category != fp.DEFAULT_CATEGORY:
        try:
            related_docs = get_random_docs(Document.query.filter(and_(Document.category == doc.category, Document.id != doc.id)), 5)
        except Exception as e: print(f"Error finding related docs: {e}")

    available_categories = sorted(list(fp.CATEGORY_KEYWORDS.keys()))
    if fp.DEFAULT_CATEGORY not in available_categories:
        available_categories.append(fp.DEFAULT_CATEGORY)
        available_categories.sort()

    return render_template('view_document.html', 
                           doc=doc, 
                           extracted_content=extracted_text_content_for_view, 
                           related_docs=related_docs, 
                           timedelta=timedelta,
                           # Thêm 2 biến còn thiếu ở đây
                           categories=available_categories, 
                           default_category=fp.DEFAULT_CATEGORY)

@app.route('/download/<int:document_id>')
def download_file(document_id):
    doc = db.session.get(Document, document_id)
    if not doc or doc.doc_type in ['link', 'googledrive_link']: abort(404)
    try: return send_from_directory(app.config['UPLOAD_FOLDER'], doc.filename, as_attachment=True)
    except Exception as e: flash(f"Lỗi tải file: {e}", "danger"); return redirect(url_for('view_document', document_id=document_id))

@app.route('/delete/<int:document_id>', methods=['POST'])
def delete_document(document_id):
    doc = db.session.get(Document, document_id)
    if doc:
        try:
            if doc.doc_type not in ['link', 'googledrive_link']:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], doc.filename)
                if os.path.exists(filepath): os.remove(filepath)
            db.session.delete(doc); db.session.commit()
            flash(f'Đã xóa thành công tài liệu "{doc.filename}".', 'success')
        except Exception as e: db.session.rollback(); flash(f'Lỗi khi xóa tài liệu: {e}', 'danger')
    else: flash(f"Tài liệu không tồn tại.", "warning")
    return redirect(url_for('index'))

@app.route('/edit_category/<int:document_id>', methods=['POST'])
def edit_category(document_id):
    doc = db.session.get(Document, document_id)
    new_cat = request.form.get('new_category')
    valid_cats = list(fp.CATEGORY_KEYWORDS.keys()) + [fp.DEFAULT_CATEGORY]
    if doc and new_cat in valid_cats:
        try: doc.category = new_cat; db.session.commit(); flash(f'Đã cập nhật danh mục cho "{doc.filename}".', 'success')
        except Exception as e: db.session.rollback(); flash(f'Lỗi cập nhật danh mục: {e}', 'danger')
    else: flash("Tài liệu hoặc danh mục không hợp lệ.", "warning")
    return redirect(request.referrer or url_for('index'))

@app.route('/timeline', endpoint='study_timeline')
def study_timeline():
    docs_viewed_today_count = 0; docs_summarized_count = 0
    try:
        today_start_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end_utc = today_start_utc + timedelta(days=1)
        docs_viewed_today_count = db.session.query(Document.id).filter(Document.last_viewed_date.between(today_start_utc, today_end_utc)).count()
        docs_summarized_count = db.session.query(Document.id).filter(Document.user_summary.isnot(None) & (Document.user_summary != '')).count()
    except Exception as e: print(f"Error fetching timeline stats: {e}")
    
    streak_days = random.randint(0, 20); avg_session_time = random.randint(10, 45); review_queue = []
    try:
        review_docs = get_random_docs(Document, 5)
        for doc in review_docs:
            due_in_days = random.choice([1, 2, 3, 5, 7]); due_date = date.today() + timedelta(days=due_in_days)
            review_queue.append({"id": doc.id, "name": doc.filename, "due": f"sau {due_in_days} ngày"})
    except Exception as e: print(f"Error fetching review queue: {e}")
    
    achievements = [{"icon": "bi-emoji-smile", "text": "Bắt đầu hành trình!"}]
    if streak_days >= 5: achievements.append({"icon": "bi-fire", "text": f"{streak_days}-Day Streak!"})
    if docs_summarized_count >= 1: achievements.append({"icon": "bi-lightbulb-fill", "text": "Viết tóm tắt đầu tiên!"})
    
    return render_template('timeline.html', docs_viewed_today=docs_viewed_today_count, total_docs_summarized=docs_summarized_count, current_streak=streak_days, avg_session_minutes=avg_session_time, review_items=review_queue, earned_achievements=achievements)

@app.route('/lazymarket', endpoint='lazy_market')
def lazy_market():
    s_job = request.args.get('suggest_job'); s_doc_id = request.args.get('doc_id', type=int); s_job_info = None
    if s_job and s_doc_id:
        doc_for_job = db.session.get(Document, s_doc_id)
        if doc_for_job: s_job_info = {'type': s_job, 'doc_filename': doc_for_job.filename}
    
    real_docs_sample = []
    try:
        docs = get_random_docs(Document, 5)
        real_docs_sample = [{"id": d.id, "name": d.filename, "category": d.category, "doc_type": d.doc_type} for d in docs]
    except Exception as e: print(f"Error fetching real docs for ranking: {e}")
    
    user_documents = [{'id': d.id, 'filename': d.filename} for d in Document.query.with_entities(Document.id, Document.filename).order_by(desc(Document.uploaded_date)).all()]
    return render_template('lazymarket.html', suggested_job_info=s_job_info, real_docs_sample=real_docs_sample, user_documents=user_documents)

@app.route('/tokenize_content', methods=['POST'])
def tokenize_content():
    try:
        data = request.get_json()
        text_content = data.get('text', '')
        category = data.get('category', 'Chưa phân loại')

        if not text_content:
            return jsonify({"error": "Không có nội dung để phân tích."}), 400

        normalized_content = normalize_vietnamese(text_content)
        found_keywords = set()

        # Lấy danh sách từ khóa cho category được chỉ định
        keywords_for_category = fp.CATEGORY_KEYWORDS.get(category, [])
        
        # Tìm kiếm các từ khóa trong nội dung
        for keyword in keywords_for_category:
            # Tìm kiếm không phân biệt dấu và là từ hoàn chỉnh
            if re.search(r'\b' + re.escape(normalize_vietnamese(keyword)) + r'\b', normalized_content):
                found_keywords.add(keyword.capitalize())

        # (Tùy chọn) Thêm logic để tìm các từ khóa chung khác nếu muốn
        
        if not found_keywords:
            return jsonify({"keywords": ["Không tìm thấy từ khóa chuyên ngành nào."]})

        return jsonify({"keywords": sorted(list(found_keywords))})

    except Exception as e:
        print(f"ERROR in /tokenize_content: {e}")
        traceback.print_exc()
        return jsonify({"error": "Lỗi server khi phân tích từ khóa."}), 500
    
# KHU VỰC ĐÃ SỬA ĐỔI
@app.route('/get_recall_data', methods=['GET'])
def get_recall_data():
    TOTAL_QUESTIONS_TO_RETURN = 3
    all_recall_items = []
    doc_ids_used = set()
    
    # Phương pháp 1: Lấy từ tóm tắt của người dùng
    try:
        docs_with_summary = Document.query.filter(Document.user_summary.isnot(None), Document.user_summary != '').all()
        if docs_with_summary:
            random.shuffle(docs_with_summary)
            for doc in docs_with_summary:
                if len(all_recall_items) >= TOTAL_QUESTIONS_TO_RETURN: break
                question_text = f"Hãy nêu lại ý chính/định nghĩa bạn đã tóm tắt cho tài liệu '{doc.filename}'."
                answer_text = doc.user_summary
                all_recall_items.append({ "q": question_text, "a": answer_text, "cat": doc.category or "Từ tóm tắt", "source_doc_id": doc.id, "type": "definition_recall" })
                doc_ids_used.add(doc.id)
    except Exception as e:
        print(f"WARNING: Lỗi khi tạo câu hỏi từ tóm tắt. Lỗi: {e}")

    # Phương pháp 2: Tạo câu hỏi điền vào chỗ trống từ nội dung
    needed = TOTAL_QUESTIONS_TO_RETURN - len(all_recall_items)
    if needed > 0:
        try:
            docs_with_content = Document.query.filter(Document.id.notin_(list(doc_ids_used)), Document.extracted_content.isnot(None), Document.extracted_content != '', Document.extracted_content.notlike('[%')).all()
            if docs_with_content:
                random.shuffle(docs_with_content)
                for doc in docs_with_content:
                    if len(all_recall_items) >= TOTAL_QUESTIONS_TO_RETURN: break
                    try:
                        q = create_fill_in_the_blank_question(doc.extracted_content)
                        if q:
                            all_recall_items.append({ "q": q["q"], "a": q["a"], "cat": doc.category or "Từ tài liệu", "source_doc_id": doc.id, "type": "fill_blank" })
                            doc_ids_used.add(doc.id)
                    except Exception as q_err:
                        print(f"WARNING: Không thể tạo câu hỏi điền vào chỗ trống cho doc_id {doc.id}. Lỗi: {q_err}")
        except Exception as e:
            print(f"WARNING: Lỗi khi truy vấn tài liệu có nội dung. Lỗi: {e}")

    # Phương pháp 3: Dùng câu hỏi mặc định làm phương án cuối
    needed = TOTAL_QUESTIONS_TO_RETURN - len(all_recall_items)
    if needed > 0:
        defaults = [
            {"q": "Trong Python, `list` và `tuple` khác nhau thế nào?", "a": "Tuple không thể thay đổi (immutable), list có thể thay đổi (mutable).", "cat": "Lập trình", "type": "default"},
            {"q": "GDP là viết tắt của gì?", "a": "Gross Domestic Product (Tổng sản phẩm quốc nội)", "cat": "Kinh tế học", "type": "default"}
        ]
        all_recall_items.extend(get_unique_random_elements(defaults, needed))
        
    # Trả về kết quả
    if not all_recall_items: 
        return jsonify([{"q": "Hiện không có câu hỏi nào. Hãy tải và tóm tắt thêm tài liệu nhé!", "a": "", "cat": "Hệ thống", "type": "error"}])
    
    return jsonify(all_recall_items)


@app.route('/ai_chat_converse', methods=['POST'])
def ai_chat_converse():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({"error": "Không có tin nhắn nào được gửi."}), 400

        ai_reply = ""
        user_message_normalized = normalize_vietnamese(user_message)
        
        if any(word in user_message_normalized for word in ["tam biet", "bye", "ket thuc", "cam on"]):
            return jsonify({"reply": random.choice(["Rất vui được hỗ trợ bạn! Hẹn gặp lại nhé!", "Chúc bạn học tốt! Nếu cần gì cứ gọi tôi."])})
        
        is_summary_request = "tom tat" in user_message_normalized
        
        search_query = user_message_normalized.replace("tom tat", "").strip()
        search_query_with_spaces = search_query.replace("_", " ")
        
        found_doc = None
        if len(search_query) > 2:
            found_doc = Document.query.filter(
                sql_func.replace(Document.filename_normalized, '_', ' ').ilike(f"%{search_query_with_spaces}%")
            ).first()
            
        if found_doc:
            if is_summary_request:
                reply = f"Đây là tóm tắt của bạn cho tài liệu '{found_doc.filename}':\n\n\"{found_doc.user_summary}\"" if found_doc.user_summary else f"Rất tiếc, bạn chưa có tóm tắt nào cho tài liệu '{found_doc.filename}'."
            else:
                reply = f"Tôi đã tìm thấy tài liệu '{found_doc.filename}'. Bạn muốn hỏi gì về nó, hay muốn xem tóm tắt?"
        else:
            if is_summary_request:
                reply = "Bạn muốn tóm tắt tài liệu nào? Vui lòng cho tôi biết tên đầy đủ và chính xác hơn nhé."
            elif any(word in user_message_normalized for word in ["chao", "hello", "hi"]):
                random_doc = get_random_docs(Document, 1)
                if random_doc:
                    reply = f"Chào bạn! Bạn có muốn thảo luận về tài liệu '{random_doc[0].filename}' hoặc một chủ đề nào khác không?"
                else:
                    reply = "Chào bạn! Hôm nay bạn muốn thảo luận về chủ đề nào?"
            else:
                reply = f"Tôi không tìm thấy tài liệu nào khớp với '{user_message}'. Bạn có thể thử lại với tên khác không?"

        return jsonify({"reply": reply})

    except Exception as e:
        print(f"ERROR in /ai_chat_converse: {e}")
        traceback.print_exc()
        return jsonify({"error": "Xin lỗi, tôi đang gặp chút sự cố và không thể trả lời ngay. Bạn thử lại sau nhé."}), 500

# --- Chạy ứng dụng ---
def create_db():
     if not os.path.exists(os.path.join(basedir, 'studyvault.db')):
        with app.app_context():
            try: db.create_all(); print("Database created!")
            except Exception as e: print(f"Error creating database: {e}")

def backfill_normalized_names():
    with app.app_context():
        print("Starting to backfill normalized filenames...")
        docs = Document.query.filter(Document.filename_normalized.is_(None)).all()
        if not docs: print("No documents to update."); return
        for doc in docs: doc.filename_normalized = normalize_vietnamese(doc.filename)
        try: db.session.commit(); print(f"Successfully updated {len(docs)} documents.")
        except Exception as e: db.session.rollback(); print(f"An error occurred during backfill: {e}")

@app.route('/document/<int:doc_id>/win_criteria', methods=['PUT'])
def update_win_criteria(doc_id):
    doc = db.session.get(Document, doc_id)
    if not doc:
        return jsonify({"error": "Tài liệu không tồn tại."}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Dữ liệu không hợp lệ."}), 400

    try:
        doc.win_criteria_description = data.get('description', doc.win_criteria_description)
        
        # Chuyển đổi target_score sang integer, xử lý nếu rỗng
        target_score_str = data.get('target_score')
        if target_score_str is not None and target_score_str != '':
            doc.target_score = int(target_score_str)
        else:
            doc.target_score = None # Cho phép xóa mục tiêu
        
        db.session.commit()
        return jsonify({
            "message": "Cập nhật mục tiêu thành công!",
            "win_criteria_description": doc.win_criteria_description,
            "target_score": doc.target_score
        })

    except (ValueError, TypeError):
        return jsonify({"error": "Điểm mục tiêu phải là một con số."}), 400
    except Exception as e:
        db.session.rollback()
        print(f"ERROR updating win criteria for doc {doc_id}: {e}")
        return jsonify({"error": "Lỗi server khi cập nhật mục tiêu."}), 500

# --- API MỚI ĐỂ GHI NHẬN KẾT QUẢ THỰC TẾ ---
@app.route('/document/<int:doc_id>/result', methods=['POST'])
def log_actual_result(doc_id):
    doc = db.session.get(Document, doc_id)
    if not doc:
        return jsonify({"error": "Tài liệu không tồn tại."}), 404

    data = request.get_json()
    if not data or 'actual_score' not in data:
        return jsonify({"error": "Dữ liệu không hợp lệ, thiếu điểm thực tế."}), 400
        
    try:
        # Chuyển đổi actual_score sang integer, xử lý nếu rỗng
        actual_score_str = data.get('actual_score')
        if actual_score_str is not None and actual_score_str != '':
             doc.actual_score = int(actual_score_str)
        else:
            doc.actual_score = None # Cho phép xóa kết quả

        db.session.commit()
        return jsonify({
            "message": "Ghi nhận kết quả thành công!",
            "actual_score": doc.actual_score
        })

    except (ValueError, TypeError):
        return jsonify({"error": "Điểm thực tế phải là một con số."}), 400
    except Exception as e:
        db.session.rollback()
        print(f"ERROR logging result for doc {doc_id}: {e}")
        return jsonify({"error": "Lỗi server khi ghi nhận kết quả."}), 500

@app.route('/api/generate_questions_from_summary', methods=['POST'])
def generate_questions_from_summary():
    """
    API giả lập việc AI tạo câu hỏi từ một đoạn tóm tắt.
    Trong thực tế, đây sẽ là nơi gọi đến một mô hình ngôn ngữ lớn (LLM).
    """
    data = request.get_json()
    summary_text = data.get('summary_text', '').lower()
    
    # --- Logic giả lập dựa trên từ khóa ---
    questions = []
    
    if 'điện trường' in summary_text and 'tác dụng lực' in summary_text:
        questions = [
            {"id": 1, "q": "Điện trường là gì và tính chất cơ bản nhất của nó là gì?", "type": "Định nghĩa"},
            {"id": 2, "q": "Làm thế nào để có thể phát hiện sự tồn tại của điện trường tại một điểm?", "type": "Khái niệm"},
            {"id": 3, "q": "Nếu một electron (điện tích âm) bay vào một điện trường, nó sẽ di chuyển cùng chiều hay ngược chiều với chiều của vector cường độ điện trường?", "type": "Vận dụng"}
        ]
    elif 'lực điện' in summary_text:
         questions = [
            {"id": 1, "q": "Phát biểu công thức của lực điện (lực Coulomb).", "type": "Công thức"},
            {"id": 2, "q": "Lực điện là lực hút hay đẩy khi hai điện tích trái dấu? Cùng dấu?", "type": "Khái niệm"}
        ]
    else:
        questions.append({"id": 0, "q": "Nội dung tóm tắt chưa đủ rõ ràng để AI có thể tạo câu hỏi. Vui lòng cung cấp thêm chi tiết về các định nghĩa hoặc công thức.", "type": "Thông báo"})

    return jsonify(questions)

@app.route('/document/<int:doc_id>/objectives', methods=['POST'])
def add_objective(doc_id):
    data = request.get_json()
    description = data.get('description', '').strip()
    parent_id = data.get('parent_id')
    if not description:
        return jsonify({"error": "Nội dung không được để trống"}), 400

    new_obj = LearningObjective(description=description, document_id=doc_id, parent_id=parent_id)
    db.session.add(new_obj)
    db.session.commit()
    return jsonify({"id": new_obj.id, "description": new_obj.description, "is_completed": new_obj.is_completed}), 201

@app.route('/objective/<int:obj_id>', methods=['DELETE'])
def delete_objective(obj_id):
    obj = db.session.get(LearningObjective, obj_id)
    if not obj:
        return jsonify({"error": "Mục tiêu không tồn tại"}), 404
    db.session.delete(obj)
    db.session.commit()
    return jsonify({"message": "Xóa thành công"}), 200

@app.route('/objective/<int:obj_id>/toggle', methods=['PUT'])
def toggle_objective(obj_id):
    obj = db.session.get(LearningObjective, obj_id)
    if not obj:
        return jsonify({"error": "Mục tiêu không tồn tại"}), 404
    obj.is_completed = not obj.is_completed
    db.session.commit()
    return jsonify({"is_completed": obj.is_completed}), 200

@app.route('/document/<int:doc_id>/objectives_tree', methods=['GET'])
def get_objectives_tree(doc_id):
    if not db.session.get(Document, doc_id):
        return jsonify({"error": "Tài liệu không tồn tại."}), 404
    
    all_objectives = LearningObjective.query.filter_by(document_id=doc_id).all()
    tree = build_objectives_tree(all_objectives)
    return jsonify(tree)



if __name__ == '__main__':
    create_db()
    # Bỏ comment dòng sau và chạy server MỘT LẦN để cập nhật dữ liệu cũ nếu cần
    # with app.app_context():
    #     backfill_normalized_names()
    app.run(debug=True)