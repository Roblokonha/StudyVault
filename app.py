# app.py
# -*- coding: utf-8 -*-

import os
import traceback
import random # Thêm để mô phỏng AI và dữ liệu
from datetime import datetime, date, timedelta # Thêm date, timedelta
from flask import (Flask, render_template, request, redirect, url_for, flash,
                   send_from_directory, abort)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from sqlalchemy import or_, and_ # Thêm and_
from sqlalchemy.sql.expression import func
from sqlalchemy.exc import SQLAlchemyError

# Giả sử file_processor.py nằm trong thư mục utils cùng cấp với app.py
# Chúng ta sẽ không dùng nhiều đến nó trong bản demo này
try:
    import utils.file_processor as fp
except ImportError:
    # Fallback nếu không có file_processor hoặc có lỗi import
    class MockFileProcessor:
        DEFAULT_CATEGORY = "Chưa phân loại"
        CATEGORY_KEYWORDS = { # Giả lập một số category cơ bản
            "Lập trình": ["python", "java", "code", "script", "lập trình"],
            "Kinh tế học": ["kinh tế", "thị trường", "gdp", "lạm phát"],
            "Toán học": ["toán", "công thức", "phương trình", "tích phân"],
            "Ngoại ngữ": ["english", "tiếng anh", "từ vựng", "grammar"]
        }
        def extract_text(self, filepath): return None # Không trích xuất thật
        def extract_keywords(self, text): return [] # Không trích xuất thật
        def categorize_document(self, keywords): # Phân loại giả lập rất cơ bản
            for cat, keys in self.CATEGORY_KEYWORDS.items():
                if any(k in ' '.join(keywords).lower() for k in keys):
                    return cat
            return self.DEFAULT_CATEGORY
    fp = MockFileProcessor()
    print("WARNING: 'utils.file_processor' not found or failed to import. Using mock processor.")


# --- Khởi tạo App và Cấu hình ---
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads/')
# Mở rộng các định dạng file cho text/pdf/docx
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'docx'}
# Định dạng video được phép (ví dụ)
app.config['ALLOWED_VIDEO_EXTENSIONS'] = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
# Định dạng ảnh được phép
app.config['ALLOWED_IMAGE_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

app.config['SECRET_KEY'] = 'thay_the_bang_mot_key_bi_mat_thuc_su!' # **QUAN TRỌNG: Thay đổi key này!**
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'studyvault.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
ITEMS_PER_PAGE = 10

# --- Model Dữ liệu (Phiên bản cuối) ---
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(300), nullable=False, unique=True) # Sẽ lưu URL cho link/gdrive
    keywords = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True, default=fp.DEFAULT_CATEGORY)
    uploaded_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_viewed_date = db.Column(db.DateTime, nullable=True)
    doc_type = db.Column(db.String(20), nullable=False, default='file', server_default='file') # pdf, docx, txt, link, image, video, googledrive_link

    # --- Trường mới được thêm ---
    engagement_level = db.Column(db.String(50), nullable=True) # 'hiểu qua', 'học sâu', 'tham khảo'
    context_event = db.Column(db.String(150), nullable=True) # 'Project X', 'Thi giữa kỳ', 'Kỹ năng mềm'
    custom_note = db.Column(db.Text, nullable=True)
    user_summary = db.Column(db.Text, nullable=True) # Tóm tắt 1 dòng của user
    ai_topic_label = db.Column(db.String(100), nullable=True) # Nhãn do AI mô phỏng gợi ý

    def __repr__(self):
        return f'<Document {self.id}: {self.filename} ({self.doc_type})>'

# --- Helper Functions ---
def allowed_file(filename):
    """Kiểm tra file văn bản/pdf/docx"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def allowed_image(filename):
    """Kiểm tra file ảnh"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_IMAGE_EXTENSIONS']

def allowed_video(filename):
    """Kiểm tra file video"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_VIDEO_EXTENSIONS']

def is_google_drive_link(url):
    """Kiểm tra sơ bộ URL Google Drive (rất cơ bản)"""
    return url and "drive.google.com" in url.lower()

# --- Routes ---
@app.route('/')
def index():
    pagination_data = None; documents_on_page = []; suggested_docs = []
    search_query = request.args.get('search_query', '').strip()
    category_filter = request.args.get('category', '').strip()
    # Lấy danh sách category từ DB hoặc từ cấu hình fp
    available_categories = sorted(list(fp.CATEGORY_KEYWORDS.keys()))
    if fp.DEFAULT_CATEGORY not in available_categories: available_categories.append(fp.DEFAULT_CATEGORY); available_categories.sort()
    # Hoặc lấy category động từ DB:
    # try:
    #     categories_from_db = db.session.query(Document.category).distinct().all()
    #     available_categories = sorted([cat[0] for cat in categories_from_db if cat[0]])
    # except Exception as cat_err:
    #     print(f"Error fetching categories from DB: {cat_err}")
    #     # Fallback to predefined categories if DB query fails
    #     available_categories = sorted(list(fp.CATEGORY_KEYWORDS.keys()))
    #     if fp.DEFAULT_CATEGORY not in available_categories: available_categories.append(fp.DEFAULT_CATEGORY); available_categories.sort()

    try:
        page = request.args.get('page', 1, type=int)
        query = Document.query
        if search_query: query = query.filter(or_(Document.filename.ilike(f"%{search_query}%"), Document.keywords.ilike(f"%{search_query}%")))
        if category_filter: query = query.filter(Document.category == category_filter)
        query = query.order_by(Document.uploaded_date.desc())
        pagination_data = query.paginate(page=page, per_page=ITEMS_PER_PAGE, error_out=False)
        documents_on_page = pagination_data.items if pagination_data else []
        try:
            # Gợi ý: Tài liệu chưa xem HOẶC chưa có thông tin ngữ cảnh
            suggested_docs = Document.query.filter(
                or_(
                    Document.last_viewed_date.is_(None),
                    Document.engagement_level.is_(None),
                    Document.context_event.is_(None)
                )
            ).order_by(func.random()).limit(3).all()
        except Exception as suggest_err: print(f"WARNING: Cannot get suggested docs: {suggest_err}")
    except Exception as db_err:
        flash(f"Lỗi khi truy vấn dữ liệu: {db_err}", "danger"); print(f"ERROR querying database: {db_err}"); traceback.print_exc()
    try:
        return render_template('index.html', pagination=pagination_data, documents=documents_on_page, categories=available_categories, search_query=search_query, category_filter=category_filter, default_category=fp.DEFAULT_CATEGORY, suggested_docs=suggested_docs )
    except Exception as render_err:
        flash(f"Lỗi nghiêm trọng khi hiển thị trang: {render_err}", "danger"); print(f"ERROR rendering template: {render_err}"); traceback.print_exc()
        return "Đã xảy ra lỗi nghiêm trọng khi tải trang.", 500

@app.route('/upload', methods=['GET', 'POST'], endpoint='upload_file')
def upload_file():
    if request.method == 'POST':
        upload_type = request.form.get('upload_type')
        filename = None
        filepath = None # Sẽ là path vật lý hoặc URL
        doc_to_save = None
        file_storage = None
        doc_type = upload_type # Mặc định

        try:
            if upload_type == 'file':
                if 'document_file' not in request.files: raise ValueError('Không có file được chọn cho loại "File"')
                file_storage = request.files['document_file']
                if file_storage.filename == '': raise ValueError('Chưa chọn file nào')
                if not allowed_file(file_storage.filename): raise ValueError('Định dạng file không hợp lệ (cần PDF, DOCX, TXT).')

                filename = secure_filename(file_storage.filename)
                file_ext = filename.rsplit('.', 1)[1].lower()
                doc_type = file_ext # Cụ thể hóa type (pdf, docx, txt)
                filepath = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                if Document.query.filter_by(filepath=filepath).first(): raise ValueError(f'File "{filename}" đã tồn tại.')

                file_storage.save(filepath)
                # Trích xuất text và keywords (dùng mock nếu cần)
                text_content = fp.extract_text(filepath) # Sẽ là None nếu dùng mock
                keywords_list = fp.extract_keywords(text_content) if text_content else [] # Sẽ là [] nếu dùng mock
                category = fp.categorize_document(keywords_list) if keywords_list else fp.DEFAULT_CATEGORY # Sẽ là default nếu dùng mock
                keywords_str = ', '.join(keywords_list) if keywords_list else None
                doc_to_save = Document(filename=filename, filepath=filepath, keywords=keywords_str, category=category, doc_type=doc_type)

            elif upload_type == 'link':
                doc_url = request.form.get('document_url')
                if not doc_url: raise ValueError('Chưa nhập URL cho loại "Link Web"')
                if Document.query.filter(Document.filepath == doc_url).first(): raise ValueError(f'Link "{doc_url}" đã tồn tại.')

                filename = doc_url # Hiển thị URL làm tên
                filepath = doc_url # Lưu URL vào filepath
                keywords_str = "link, web-content, online-resource, demo" # Keywords mô phỏng
                category = "Link Web"
                doc_type = 'link'
                doc_to_save = Document(filename=filename, filepath=filepath, keywords=keywords_str, category=category, doc_type=doc_type)

            elif upload_type == 'image':
                if 'document_image' not in request.files: raise ValueError('Không có file ảnh được chọn')
                file_storage = request.files['document_image']
                if file_storage.filename == '': raise ValueError('Chưa chọn file ảnh nào')
                if not allowed_image(file_storage.filename): raise ValueError('Định dạng file không hợp lệ cho loại "Ảnh".')

                filename = secure_filename(file_storage.filename)
                filepath = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                if Document.query.filter_by(filepath=filepath).first(): raise ValueError(f'Ảnh "{filename}" đã tồn tại.')

                file_storage.save(filepath)
                keywords_str = "image, picture, photo, scan, visual, demo" # Keywords mô phỏng
                category = "Hình ảnh"
                doc_type = 'image'
                doc_to_save = Document(filename=filename, filepath=filepath, keywords=keywords_str, category=category, doc_type=doc_type)

            elif upload_type == 'video':
                if 'document_video' not in request.files: raise ValueError('Không có file video được chọn')
                file_storage = request.files['document_video']
                if file_storage.filename == '': raise ValueError('Chưa chọn file video nào')
                if not allowed_video(file_storage.filename): raise ValueError('Định dạng file không hợp lệ cho loại "Video".')

                filename = secure_filename(file_storage.filename)
                filepath = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                if Document.query.filter_by(filepath=filepath).first(): raise ValueError(f'Video "{filename}" đã tồn tại.')

                file_storage.save(filepath)
                keywords_str = "video, media, recording, lecture, demo, 5min-preview"
                category = "Video"
                doc_type = 'video'
                doc_to_save = Document(filename=filename, filepath=filepath, keywords=keywords_str, category=category, doc_type=doc_type)

            elif upload_type == 'googledrive_link':
                gdrive_url = request.form.get('document_gdrive_link')
                if not gdrive_url: raise ValueError('Chưa nhập URL Google Drive')
                if not is_google_drive_link(gdrive_url): raise ValueError('URL không giống link Google Drive hợp lệ.')
                if Document.query.filter(Document.filepath == gdrive_url).first(): raise ValueError(f'Link Google Drive "{gdrive_url}" đã tồn tại.')

                filename = gdrive_url # Hiển thị URL làm tên
                filepath = gdrive_url # Lưu URL vào filepath
                keywords_str = "google-drive, cloud-link, document, shared, demo" # Keywords mô phỏng
                category = "Google Drive"
                doc_type = 'googledrive_link'
                doc_to_save = Document(filename=filename, filepath=filepath, keywords=keywords_str, category=category, doc_type=doc_type)

            else:
                raise ValueError('Loại upload không hợp lệ.')

            # Lưu vào Database
            if doc_to_save:
                db.session.add(doc_to_save)
                db.session.commit()
                flash(f'Đã lưu "{doc_to_save.filename}" ({doc_to_save.doc_type}). Category: "{doc_to_save.category}".', 'success')
                # Chuyển đến trang xem chi tiết sau khi upload thành công
                return redirect(url_for('view_document', document_id=doc_to_save.id))
            else:
                 flash('Đã xảy ra lỗi không xác định trong quá trình chuẩn bị lưu.', 'danger')
                 return redirect(request.url)

        except ValueError as ve:
            flash(str(ve), 'warning'); return redirect(request.url)
        except SQLAlchemyError as db_err:
             db.session.rollback(); flash(f'Lỗi cơ sở dữ liệu: {db_err}', 'danger'); print(f"ERROR DB during upload: {db_err}"); traceback.print_exc()
             if upload_type not in ['link', 'googledrive_link'] and filepath and os.path.exists(filepath) and not Document.query.filter_by(filepath=filepath).first():
                try: os.remove(filepath)
                except OSError: pass
             return redirect(request.url)
        except Exception as e:
            db.session.rollback(); flash(f'Lỗi không xác định khi upload: {e}', 'danger'); print(f"ERROR upload: {e}"); traceback.print_exc()
            if upload_type not in ['link', 'googledrive_link'] and filepath and os.path.exists(filepath) and not Document.query.filter_by(filepath=filepath).first():
                try: os.remove(filepath)
                except OSError: pass
            return redirect(request.url)

    return render_template('upload.html')


@app.route('/document/<int:document_id>', methods=['GET', 'POST'])
def view_document(document_id):
    doc = db.session.get(Document, document_id)
    if not doc: abort(404)

    related_docs = [] # Khởi tạo

    # Xử lý POST request
    if request.method == 'POST':
        form_marker = request.form.get('form_marker')
        try:
            if form_marker == 'update_context':
                doc.engagement_level = request.form.get('engagement_level')
                doc.context_event = request.form.get('context_event')
                doc.custom_note = request.form.get('custom_note')
                db.session.commit()
                flash('Đã cập nhật thông tin ngữ cảnh.', 'success')
            elif form_marker == 'submit_summary':
                user_summary = request.form.get('user_summary', '').strip()
                if user_summary:
                    doc.user_summary = user_summary
                    # Mô phỏng AI Labeling
                    summary_lower = user_summary.lower()
                    if any(kw in summary_lower for kw in ['code', 'python', 'lập trình', 'thuật toán']): doc.ai_topic_label = 'Chủ đề: Lập trình & CNPM'
                    elif any(kw in summary_lower for kw in ['kinh tế', 'thị trường', 'marketing', 'kinh doanh']): doc.ai_topic_label = 'Chủ đề: Kinh tế & Kinh doanh'
                    elif any(kw in summary_lower for kw in ['toán', 'công thức', 'phương trình', 'tích phân']): doc.ai_topic_label = 'Chủ đề: Toán học'
                    elif any(kw in summary_lower for kw in ['luật', 'điều khoản', 'pháp lý']): doc.ai_topic_label = 'Chủ đề: Pháp luật'
                    else: possible_labels = ['Chủ đề: Khoa học Xã hội', 'Chủ đề: Kỹ thuật Chung', 'Chủ đề: Kiến thức Tổng quát']; doc.ai_topic_label = random.choice(possible_labels)
                    db.session.commit()
                    flash(f'Đã lưu tóm tắt của bạn. AI gợi ý: {doc.ai_topic_label}', 'info')
                else:
                    flash('Bạn chưa nhập tóm tắt.', 'warning')
            else:
                flash('Yêu cầu không hợp lệ.', 'warning')
            return redirect(url_for('view_document', document_id=document_id))
        except SQLAlchemyError as e:
            db.session.rollback(); flash(f'Lỗi khi lưu dữ liệu: {e}', 'danger'); print(f"ERROR saving context/summary: {e}")
        except Exception as e:
             flash(f'Lỗi không xác định: {e}', 'danger'); print(f"ERROR processing POST in view_document: {e}")

    # Xử lý GET request
    extracted_text_content = None
    physical_filepath_to_check = None

    if doc.doc_type not in ['link', 'googledrive_link']:
        try:
            upload_dir = os.path.abspath(app.config['UPLOAD_FOLDER'])
            physical_filepath_to_check = os.path.join(upload_dir, doc.filename)
        except Exception as path_err: print(f"ERROR constructing file path for doc {document_id}: {path_err}")

    if request.method == 'GET':
        try:
            doc.last_viewed_date = datetime.utcnow(); db.session.commit()
        except SQLAlchemyError as e: db.session.rollback(); print(f"ERROR updating last_viewed_date: {e}")

    try:
        if doc.doc_type in ['pdf', 'docx', 'txt', 'file']:
             if physical_filepath_to_check and os.path.exists(physical_filepath_to_check):
                 extracted_text_content = fp.extract_text(physical_filepath_to_check) # Sẽ là None nếu dùng mock
                 if not extracted_text_content: extracted_text_content = "[Không trích xuất được nội dung văn bản hoặc file trống]"
             else: extracted_text_content = f"[Lỗi: Không tìm thấy file gốc]"
    except Exception as extract_error:
        print(f"ERROR extracting content for view page (doc {document_id}): {extract_error}")
        extracted_text_content = "[Lỗi khi trích xuất nội dung xem trước]"

    # Tìm tài liệu liên quan
    if request.method == 'GET' and doc.category and doc.category != fp.DEFAULT_CATEGORY:
        try:
            related_docs = Document.query.filter(
                and_(Document.category == doc.category, Document.id != doc.id)
            ).order_by(func.random()).limit(5).all()
        except Exception as related_err:
            print(f"Error finding related documents for doc {doc.id}: {related_err}")
            related_docs = []

    return render_template(
        'view_document.html',
        doc=doc,
        extracted_content=extracted_text_content,
        related_docs=related_docs
    )


@app.route('/download/<int:document_id>')
def download_file(document_id):
    doc = db.session.get(Document, document_id)
    if not doc: abort(404)
    if doc.doc_type in ['link', 'googledrive_link']:
        flash("Không thể tải về Link Web hoặc Link Google Drive.", "warning")
        return redirect(url_for('view_document', document_id=doc.id))

    try:
        upload_dir = os.path.abspath(app.config['UPLOAD_FOLDER'])
        safe_filename = secure_filename(doc.filename)
        file_path_to_send = os.path.join(upload_dir, safe_filename)

        if not os.path.exists(file_path_to_send):
            print(f"File not found on download attempt: {file_path_to_send}")
            original_path_maybe = os.path.join(upload_dir, doc.filename)
            if os.path.exists(original_path_maybe): file_path_to_send = original_path_maybe
            else: abort(404)

        if not os.path.abspath(file_path_to_send).startswith(upload_dir):
             print(f"Potential path traversal detected on download: {file_path_to_send}"); abort(403)

        return send_from_directory(upload_dir, os.path.basename(file_path_to_send), as_attachment=True)

    except Exception as e:
        flash(f"Lỗi tải file: {e}", "danger"); print(f"ERROR download: {e}")
        return redirect(url_for('view_document', document_id=doc.id))

@app.route('/delete/<int:document_id>', methods=['POST'])
def delete_document(document_id):
    doc = db.session.get(Document, document_id)
    if not doc: flash(f"Tài liệu ID {document_id} không tồn tại.", "warning"); return redirect(url_for('index'))

    filename_to_delete = doc.filename
    filepath_stored = doc.filepath

    try:
        if doc.doc_type not in ['link', 'googledrive_link']:
            try:
                upload_dir = os.path.abspath(app.config['UPLOAD_FOLDER'])
                physical_path_to_delete = os.path.abspath(os.path.join(upload_dir, secure_filename(doc.filename)))

                if not physical_path_to_delete.startswith(upload_dir):
                     print(f"Potential path traversal detected on delete: {physical_path_to_delete}"); raise Exception("Path deletion attempt outside designated folder.")

                if os.path.exists(physical_path_to_delete):
                    os.remove(physical_path_to_delete); print(f"Đã xóa file vật lý: {physical_path_to_delete}")
                else: print(f"Cảnh báo: File vật lý không tồn tại để xóa: {physical_path_to_delete}.")
            except Exception as file_del_err:
                print(f"ERROR deleting physical file for doc {doc.id}: {file_del_err}")
                flash(f'Lỗi khi xóa file vật lý "{filename_to_delete}". Vui lòng kiểm tra thủ công.', 'warning')

        db.session.delete(doc)
        db.session.commit()
        flash(f'Đã xóa thành công tài liệu "{filename_to_delete}" khỏi cơ sở dữ liệu.', 'success')

    except Exception as e:
        db.session.rollback(); flash(f'Lỗi khi xóa "{filename_to_delete}" khỏi cơ sở dữ liệu: {e}', 'danger'); print(f"ERROR deleting db record: {e}"); traceback.print_exc()

    return redirect(url_for('index'))


@app.route('/edit_category/<int:document_id>', methods=['POST'])
def edit_category(document_id):
    doc = db.session.get(Document, document_id);
    if not doc: flash(f"Tài liệu ID {document_id} không tồn tại.", "warning"); return redirect(url_for('index'))
    new_cat = request.form.get('new_category')
    # Lấy category hợp lệ từ cấu hình fp
    valid_cats = list(fp.CATEGORY_KEYWORDS.keys()) + [fp.DEFAULT_CATEGORY]
    # Hoặc có thể thêm category từ DB nếu muốn linh hoạt hơn
    # try:
    #     db_cats = db.session.query(Document.category).distinct().all()
    #     valid_cats.extend([c[0] for c in db_cats if c[0] and c[0] not in valid_cats])
    # except Exception: pass # Bỏ qua lỗi lấy category từ DB

    if not new_cat or new_cat not in valid_cats: flash(f"Danh mục '{new_cat}' không hợp lệ.", "danger"); return redirect(request.referrer or url_for('index')) # Quay lại trang trước đó
    try:
        doc.category = new_cat
        db.session.commit()
        flash(f'Đã cập nhật danh mục cho "{doc.filename}".', 'success')
    except Exception as e:
        db.session.rollback(); flash(f'Lỗi cập nhật danh mục: {e}', 'danger'); print(f"ERROR updating category: {e}"); traceback.print_exc()
    return redirect(request.referrer or url_for('index')) # Quay lại trang trước đó (index hoặc view_doc)


@app.route('/timeline', endpoint='study_timeline')
def study_timeline():
    docs_viewed_today_count = 0
    docs_summarized_count = 0
    try:
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())
        docs_viewed_today_count = db.session.query(Document.id).filter(
            Document.last_viewed_date >= today_start, Document.last_viewed_date <= today_end
        ).count()
        docs_summarized_count = db.session.query(Document.id).filter(
            Document.user_summary.isnot(None) & (Document.user_summary != '')
        ).count()
    except Exception as e: print(f"Error fetching real stats for timeline: {e}")

    streak_days = random.choice([0] + list(range(3, 16)))
    avg_session_time = random.randint(10, 45)
    review_queue = []
    try:
        random_docs = Document.query.order_by(func.random()).limit(5).all()
        review_queue_with_dates = []
        for i, doc_item in enumerate(random_docs):
            due_in_days = random.choice([1, 3, 7])
            due_date = date.today() + timedelta(days=due_in_days)
            review_queue_with_dates.append({
                "id": doc_item.id, # Thêm ID để có thể link
                "name": doc_item.filename,
                "due": f"sau {due_in_days} ngày ({due_date.strftime('%d/%m')})"
            })
        review_queue = review_queue_with_dates
    except Exception as e:
        print(f"Error fetching random docs for review queue: {e}")
        review_queue = [{"id": 0, "name": "Lỗi lấy dữ liệu ôn tập", "due": "N/A"}]

    achievements = []
    if streak_days >= 5: achievements.append({"icon": "bi-fire", "text": f"{streak_days}-Day Streak!"})
    if docs_summarized_count >= 1: achievements.append({"icon": "bi-lightbulb-fill", "text": "Viết tóm tắt đầu tiên!"})
    if docs_summarized_count >= 10: achievements.append({"icon": "bi-award-fill", "text": "Chuyên gia tóm tắt (10+)"})
    if docs_viewed_today_count >= 5: achievements.append({"icon": "bi-book-half", "text": "Siêng năng hôm nay (5+)"})
    if not achievements: achievements.append({"icon": "bi-emoji-smile", "text": "Bắt đầu hành trình!"})

    return render_template(
        'timeline.html',
        docs_viewed_today=docs_viewed_today_count,
        total_docs_summarized=docs_summarized_count,
        current_streak=streak_days,
        avg_session_minutes=avg_session_time,
        review_items=review_queue,
        earned_achievements=achievements
    )

@app.route('/lazymarket', endpoint='lazy_market')
def lazy_market():
    # Lấy thông tin job gợi ý (nếu có)
    s_job = request.args.get('suggest_job')
    s_doc_id = request.args.get('doc_id', type=int) # Vẫn cần cẩn thận nếu doc_id không hợp lệ
    s_job_info = None
    if s_job and s_doc_id:
        # Sử dụng try-except để bắt lỗi nếu doc_id không hợp lệ hoặc không tìm thấy doc
        try:
            doc_for_job = db.session.get(Document, s_doc_id)
            if doc_for_job:
                 s_job_info = {'type': s_job, 'doc_filename': doc_for_job.filename}
            else:
                 s_job_info = {'type': s_job, 'doc_filename': f"(ID: {s_doc_id} không tìm thấy)"}
        except Exception as e_job:
             print(f"Error getting suggested job info: {e_job}")
             s_job_info = {'type': s_job, 'doc_filename': f"(Lỗi khi lấy ID: {s_doc_id})"}


    # --- Lấy mẫu tài liệu thực tế cho BXH ---
    real_docs_sample = []
    try:
        real_docs_for_ranking = Document.query.with_entities(
            Document.id, Document.filename, Document.category, Document.doc_type
        ).order_by(func.random()).limit(5).all()
        real_docs_sample = [
            {"id": d.id, "name": d.filename, "category": d.category, "doc_type": d.doc_type} for d in real_docs_for_ranking
        ]
    except Exception as e_rank:
        print(f"Error fetching real docs for LazyMarket ranking: {e_rank}")

    # --- LẤY DANH SÁCH TÀI LIỆU CHO FORM ĐĂNG BÀI ---
    user_documents = []
    try:
        # Lấy ID và tên file, sắp xếp theo ngày tải lên mới nhất
        all_user_docs = Document.query.with_entities(
            Document.id, Document.filename
        ).order_by(desc(Document.uploaded_date)).all() # Sắp xếp để file mới nhất lên đầu dropdown
        user_documents = [{'id': d.id, 'filename': d.filename} for d in all_user_docs]
        print(f"Fetched {len(user_documents)} documents for forum select.") # Log để kiểm tra
    except Exception as e_docs:
        print(f"Error fetching user documents for forum form: {e_docs}")
        flash("Lỗi: Không thể tải danh sách tài liệu của bạn.", "warning") # Thông báo lỗi nhẹ nhàng

    return render_template(
        'lazymarket.html',
        suggested_job_info=s_job_info,
        real_docs_sample=real_docs_sample,
        user_documents=user_documents # Luôn truyền biến này, dù là list rỗng
    )

# --- Chạy ứng dụng ---
def create_db():
     # Hàm tiện ích để tạo DB nếu chưa có khi chạy trực tiếp
     if not os.path.exists(os.path.join(basedir, 'studyvault.db')):
        with app.app_context():
            try:
                db.create_all()
                print("Database created!")
            except Exception as e_create:
                 print(f"Error creating database: {e_create}")

if __name__ == '__main__':
    create_db() # Gọi hàm tạo DB
    app.run(debug=True) # Bật debug mode để dễ theo dõi lỗi