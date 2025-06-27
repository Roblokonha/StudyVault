document.addEventListener('DOMContentLoaded', function() {
    const documentsData = JSON.parse(document.body.dataset.documentsDataForJs || '[]');
    const userShortTermModeActive = document.body.dataset.userStmActive === 'true';
    const userShortTermFocusKeywords = document.body.dataset.userStmKeywords || '';
    const userShortTermIntensity = document.body.dataset.userStmIntensity || 'x3';
    const todayDate = new Date(document.body.dataset.todayDate || new Date().toISOString().split('T')[0]);


    const workspaceTabs = document.getElementById('workspaceTabs');
    const documentRows = document.querySelectorAll('tr.document-row');
    const noResultsRow = document.querySelector('tbody tr td[colspan="5"]');

    
    // THÊM MỚI: LOGIC TỰ ĐỘNG CHỌN TAB DỰA TRÊN TÀI LIỆU MỚI NHẤT
    if (workspaceTabs && documentsData.length > 0) {
        const latestDocument = documentsData[0]; 
        const tabs = workspaceTabs.querySelectorAll('a.nav-link');
        let targetTabId = 'all'; 

        if (latestDocument.is_goal_related) {
            targetTabId = 'focus'; 
        } else {
            targetTabId = 'sandbox'; 
        }
        
        
        tabs.forEach(tab => {
            tab.classList.remove('active');
            if (tab.dataset.tabTarget === targetTabId) {
                tab.classList.add('active');
            }
        });
    }

    function filterDocuments(targetTab) {
        let visibleCount = 0;
        documentRows.forEach(row => {
            const docType = row.dataset.docType;
            let shouldShow = false;

            if (targetTab === 'all') {
                shouldShow = true;
            } else if (targetTab === 'focus' && docType === 'goal-related') {
                shouldShow = true;
            } else if (targetTab === 'sandbox' && docType === 'sandbox') {
                shouldShow = true;
            }

            if (shouldShow) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });

        if (noResultsRow) {
            noResultsRow.parentElement.style.display = (visibleCount === 0) ? '' : 'none';
        }
    }

    function displayMascotMessage(icon, message, type = 'info') {
        const focusLockMascotEl = document.getElementById('focusLockMascot');
        const mascotIconEl = document.getElementById('mascotIcon');
        const mascotMessageEl = document.getElementById('mascotMessage');
        if (!focusLockMascotEl || !mascotIconEl || !mascotMessageEl) return;
        mascotIconEl.textContent = icon;
        mascotMessageEl.textContent = message;
        focusLockMascotEl.style.display = 'block';
        mascotMessageEl.className = 'small fst-italic mt-1 ';
        if (type === 'warning') mascotMessageEl.classList.add('text-danger');
        else if (type === 'success') mascotMessageEl.classList.add('text-success');
        else mascotMessageEl.classList.add('text-muted');
    }

    function checkAnswerSimilarity(userAnswer, correctAnswer) {
        if (!userAnswer || !correctAnswer) return false;
        const normalize = (str) => str.toLowerCase().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g,"").replace(/\s{2,}/g," ");
        const ua = normalize(userAnswer);
        const ca = normalize(correctAnswer);
        const correctWords = new Set(ca.split(' ').filter(w => w.length > 1));
        const userWords = new Set(ua.split(' '));
        if (correctWords.size === 0) return ua === ca;
        let matchCount = 0;
        for (const word of userWords) {
            if (correctWords.has(word)) {
                matchCount++;
            }
        }
        const similarity = matchCount / correctWords.size;
        return similarity > 0.7;
    }

    var editModalEl = document.getElementById('editCategoryModal');
    if (editModalEl) {
        editModalEl.addEventListener('show.bs.modal', function (event) {
            var button = event.relatedTarget;
            var docId = button.getAttribute('data-doc-id');
            var docFilename = button.getAttribute('data-doc-filename');
            var currentCategory = button.getAttribute('data-doc-category');
            var modalFilenameEl = editModalEl.querySelector('#modal-doc-filename');
            var categorySelectEl = editModalEl.querySelector('#edit-category-select');
            var formEl = editModalEl.querySelector('#editCategoryForm');
            if(modalFilenameEl) modalFilenameEl.textContent = docFilename;
            if(categorySelectEl) {
                let categoryExists = false;
                for(let i=0; i < categorySelectEl.options.length; i++) {
                    if (categorySelectEl.options[i].value === currentCategory) {
                        categoryExists = true; break;
                    }
                }
                categorySelectEl.value = categoryExists ? currentCategory : (categorySelectEl.options[0] ? categorySelectEl.options[0].value : '');
             }
            if(formEl) formEl.action = '/edit_category/' + docId;
        });
    }

    const avatarSelection = document.getElementById('avatarSelection');
    if (avatarSelection) {
        const selectedAvatarInput = document.getElementById('selectedAvatarInput');
        if (!selectedAvatarInput) {
            console.error("Error: #selectedAvatarInput not found.");
            return;
        }
        avatarSelection.addEventListener('click', function(event) {
            const clickedAvatar = event.target.closest('img');
            if (clickedAvatar && clickedAvatar.dataset.avatarId) {
                avatarSelection.querySelectorAll('img').forEach(img => {
                    img.classList.remove('selected');
                });
                clickedAvatar.classList.add('selected');
                selectedAvatarInput.value = clickedAvatar.dataset.avatarId;
            }
        });
    }

    const colorThemeSelection = document.getElementById('colorThemeSelection');
    if (colorThemeSelection) {
        const selectedColorThemeInput = document.getElementById('selectedColorThemeInput');
        if (!selectedColorThemeInput) {
            console.error("Error: #selectedColorThemeInput not found.");
            return;
        }
        colorThemeSelection.addEventListener('click', function(event) {
            const clickedColorBox = event.target.closest('.color-box');
            if (clickedColorBox && clickedColorBox.dataset.colorTheme) {
                colorThemeSelection.querySelectorAll('.color-box').forEach(box => {
                    box.classList.remove('selected');
                });
                clickedColorBox.classList.add('selected');
                selectedColorThemeInput.value = clickedColorBox.dataset.colorTheme;
            }
        });
    }

    const profileSetupModal = document.getElementById('profileSetupModal');
    if (profileSetupModal) {
        profileSetupModal.addEventListener('show.bs.modal', function () {
            const currentAvatarInput = document.getElementById('selectedAvatarInput');
            const currentAvatarSelection = document.getElementById('avatarSelection');
            if (currentAvatarInput && currentAvatarSelection) {
                const currentSelectedAvatarId = currentAvatarInput.value;
                currentAvatarSelection.querySelectorAll('img').forEach(img => {
                    img.classList.remove('selected');
                    if (img.dataset.avatarId === currentSelectedAvatarId) {
                        img.classList.add('selected');
                    }
                });
            }

            const currentColorThemeInput = document.getElementById('selectedColorThemeInput');
            const currentColorThemeSelection = document.getElementById('colorThemeSelection');
            if (currentColorThemeInput && currentColorThemeSelection) {
                const currentSelectedColor = currentColorThemeInput.value;
                currentColorThemeSelection.querySelectorAll('.color-box').forEach(box => {
                    box.classList.remove('selected');
                    if (box.dataset.colorTheme === currentSelectedColor) {
                        box.classList.add('selected');
                    }
                });
                if (!currentSelectedColor && currentColorThemeSelection.querySelector('[data-color-theme="blue"]')) {
                    currentColorThemeSelection.querySelector('[data-color-theme="blue"]').classList.add('selected');
                    currentColorThemeInput.value = 'blue';
                }
            }
        });
    }

    const shortTermTimelineList = document.getElementById('shortTermTimelineList');
    if (userShortTermModeActive && shortTermTimelineList) {
        const endDateFromUser = new Date(document.body.dataset.userStmEndDate);

        function generateShortTermTimeline() {
            shortTermTimelineList.innerHTML = '';
            const intensityMultiplier = parseInt(userShortTermIntensity.replace('x', ''));
            const totalDuration = Math.round((endDateFromUser - todayDate) / (1000 * 60 * 60 * 24)) + 1;
            const relevantDocs = documentsData.filter(doc => {
                const normalizedDocName = (doc.filename_normalized || '').toLowerCase();
                const docKeywords = (doc.keywords || '').toLowerCase();
                const docCategory = (doc.category || '').toLowerCase();
                return userShortTermFocusKeywords.toLowerCase().split(' ').some(keyword =>
                    keyword && (normalizedDocName.includes(keyword) ||
                    docKeywords.includes(keyword) ||
                    docCategory.includes(keyword))
                );
            });

            for (let i = 0; i < totalDuration; i++) {
                const currentDay = new Date(todayDate);
                currentDay.setDate(todayDate.getDate() + i);
                const li = document.createElement('li');
                li.className = 'list-group-item';
                let activityText = `Ngày ${i + 1} (${currentDay.toLocaleDateString('vi-VN')}): `;
                let dailyActivities = [];

                for (let j = 0; j < intensityMultiplier / 3; j++) {
                    const activityType = ['Đọc', 'Tóm tắt', 'Ôn tập', 'Quiz', 'Xem video'][Math.floor(Math.random() * 5)];
                    let docTitle = 'chung chung';
                    if (relevantDocs.length > 0) {
                        docTitle = relevantDocs[Math.floor(Math.random() * relevantDocs.length)].filename;
                    } else if (documentsData.length > 0) {
                        docTitle = documentsData[Math.floor(Math.random() * documentsData.length)].filename;
                    }
                    dailyActivities.push(`${activityType} "${docTitle.substring(0,25)}..."`);
                }
                activityText += dailyActivities.join(', ') || 'Nghỉ ngơi, củng cố kiến thức';
                li.innerHTML = `<i class="bi bi-dot me-2"></i>${activityText}`;
                shortTermTimelineList.appendChild(li);
            }
        }
        generateShortTermTimeline();
    }

    const deactivateShortTermModeBtn = document.getElementById('deactivateShortTermModeBtn');
    if (deactivateShortTermModeBtn) {
        deactivateShortTermModeBtn.addEventListener('click', async function() {
            if (confirm("Bạn có chắc chắn muốn vô hiệu hóa SHORT-TERM MODE?")) {
                try {
                    const response = await fetch("/deactivate_short_term_mode", {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'}
                    });
                    const data = await response.json();
                    if (response.ok) {
                        alert(data.message);
                        window.location.reload();
                    } else {
                        alert(data.error || "Lỗi khi vô hiệu hóa chế độ.");
                    }
                } catch (error) {
                    alert("Lỗi kết nối server khi vô hiệu hóa chế độ.");
                }
            }
        });
    }

    const shortTermModeForm = document.getElementById('shortTermModeForm');
    if (shortTermModeForm) {
        const activateShortTermModeBtn = document.getElementById('activateShortTermModeBtn');
        shortTermModeForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            if (activateShortTermModeBtn) activateShortTermModeBtn.disabled = true;
            try {
                const formData = new FormData(shortTermModeForm);
                const response = await fetch("/activate_short_term_mode", {
                    method: 'POST',
                    body: formData 
                });
                const data = await response.json(); 
                if (response.ok && data.success) {
                    if (data.redirect_url) {
                        window.location.href = data.redirect_url; 
                    } else {
                        alert(data.message || 'Chế độ đã được kích hoạt.');
                        window.location.reload(); 
                    }
                } else {
                    alert(data.error || 'Đã xảy ra lỗi khi kích hoạt SHORT-TERM MODE.');
                    if (activateShortTermModeBtn) activateShortTermModeBtn.disabled = false;
                }
            } catch (error) {
                console.error('Lỗi khi gửi yêu cầu kích hoạt SHORT-TERM MODE:', error);
                alert('Đã xảy ra lỗi kết nối. Vui lòng thử lại.');
                if (activateShortTermModeBtn) activateShortTermModeBtn.disabled = false;
            }
        });
    }

    const focusLockModalEl = document.getElementById('focusLockModal');
    if (focusLockModalEl) {
        const focusLockBtn = document.getElementById('focusLockBtn');
        const focusQuestionEl = document.getElementById('focusQuestion');
        const focusQuestionCategoryEl = document.getElementById('focusQuestionCategory');
        const focusAnswerInput = document.getElementById('focusAnswerInput');
        const checkFocusAnswerBtn = document.getElementById('checkFocusAnswerBtn');
        const focusFeedbackEl = document.getElementById('focusFeedback');
        const focusLockMascotEl = document.getElementById('focusLockMascot');
        const mascotIconEl = document.getElementById('mascotIcon');
        const mascotMessageEl = document.getElementById('mascotMessage');
        const focusLockModalLabel = document.getElementById('focusLockModalLabel');
        const focusLockIntroTextEl = document.getElementById('focusLockIntroText');

        let questionsBatch = [];
        let currentQuestionIndex = 0;
        let questionsCorrect = 0;
        const MIN_CORRECT_TO_UNLOCK = 2;
        let focusModal = new bootstrap.Modal(focusLockModalEl);
        let idleTimer = null;
        const IDLE_TIMEOUT = 3 * 60 * 1000;

        function resetIdleTimer() {
            clearTimeout(idleTimer);
            if (!focusLockModalEl.classList.contains('show')) {
                 idleTimer = setTimeout(triggerFocusLockOnIdle, IDLE_TIMEOUT);
            }
        }

        function triggerFocusLockOnIdle() {
            const anyOtherModalOpen = document.querySelector('.modal.show:not(#focusLockModal)');
            if (!focusLockModalEl.classList.contains('show') && !anyOtherModalOpen) {
                if(focusLockIntroTextEl) focusLockIntroTextEl.textContent = "Có vẻ bạn đang nghỉ ngơi? Hãy trả lời vài câu hỏi để củng cố kiến thức nhé!";
                displayMascotMessage('🤔', 'Lâu rồi không thấy bạn hoạt động. Làm vài câu hỏi ôn tập cho vui nhé!', 'info');
                startFocusLockSession(true);
                focusModal.show();
            } else {
                resetIdleTimer();
            }
        }

        function updateModalTitle() {
            if (!focusLockModalLabel) return;
            if (questionsBatch.length > 0 && currentQuestionIndex < questionsBatch.length) {
                focusLockModalLabel.innerHTML = `<i class="bi bi-unlock-fill text-primary"></i> Mở khóa (Câu ${currentQuestionIndex + 1}/${questionsBatch.length})`;
            } else if (questionsBatch.length > 0 && currentQuestionIndex >= questionsBatch.length) {
                focusLockModalLabel.innerHTML = `<i class="bi bi-unlock-fill text-primary"></i> Kết quả Mở khóa`;
            } else {
                focusLockModalLabel.innerHTML = `<i class="bi bi-unlock-fill text-primary"></i> Mở khóa Ứng dụng`;
            }
        }

        function displayCurrentQuestion() {
            if (currentQuestionIndex < questionsBatch.length) {
                const questionData = questionsBatch[currentQuestionIndex];
                if(focusQuestionEl) focusQuestionEl.textContent = questionData.q;
                if(focusQuestionCategoryEl) focusQuestionCategoryEl.textContent = `(Lĩnh vực: ${questionData.cat || 'Chung'})`;
                if(focusAnswerInput) focusAnswerInput.value = '';
                if(focusFeedbackEl) focusFeedbackEl.innerHTML = '';
                if(focusAnswerInput) focusAnswerInput.disabled = false;
                if(checkFocusAnswerBtn) {
                    checkFocusAnswerBtn.disabled = false;
                    checkFocusAnswerBtn.textContent = 'Kiểm tra';
                }
                updateModalTitle();
            } else {
                handleSessionEnd();
            }
        }

        async function startFocusLockSession(isAutoTriggered = false) {
            if(focusQuestionEl) focusQuestionEl.textContent = 'Đang tải bộ câu hỏi...';
            if(focusQuestionCategoryEl) focusQuestionCategoryEl.textContent = '';
            if(focusAnswerInput) focusAnswerInput.disabled = true;
            if(checkFocusAnswerBtn) checkFocusAnswerBtn.disabled = true;

            if (!isAutoTriggered) {
                if(focusLockMascotEl) focusLockMascotEl.style.display = 'none';
                if(focusLockIntroTextEl) focusLockIntroTextEl.textContent = "Để tiếp tục sử dụng ứng dụng, bạn cần trả lời đúng các câu hỏi ôn tập kiến thức đã học:";
            }

            questionsBatch = []; currentQuestionIndex = 0; questionsCorrect = 0;
            updateModalTitle();

            try {
                const response = await fetch('/get_recall_data');
                const data = await response.json();
                if (!response.ok || !Array.isArray(data) || data.length === 0) throw new Error(data.error || "Không thể tải bộ câu hỏi.");
                if (data[0].type === 'error') {
                     if(focusQuestionEl) focusQuestionEl.textContent = data[0].q;
                     displayMascotMessage('😿', 'Hmm, hiện tại không có câu hỏi nào cả!', 'info');
                     questionsBatch = [];
                     return;
                }
                questionsBatch = data;
                displayCurrentQuestion();
                displayMascotMessage('😼', `Bắt đầu thử thách với ${questionsBatch.length} câu hỏi nào!`);
            } catch (error) {
                if(focusQuestionEl) focusQuestionEl.textContent = error.message;
                displayMascotMessage('🙀', 'Hệ thống gặp trục trặc khi tải câu hỏi!');
            }
        }

        function handleSessionEnd() {
            if(focusAnswerInput) focusAnswerInput.disabled = true;
            if(checkFocusAnswerBtn) {
                checkFocusAnswerBtn.disabled = true;
                checkFocusAnswerBtn.textContent = 'Hoàn thành';
            }
            updateModalTitle();
            const totalAttempted = questionsBatch.length;
            if (totalAttempted === 0) {
                 if(focusFeedbackEl) focusFeedbackEl.innerHTML = `<div class="alert alert-info">Không có câu hỏi nào để hoàn thành.</div>`;
                 setTimeout(() => { if (focusModal) focusModal.hide(); }, 3000);
                 return;
            }
            if (questionsCorrect >= MIN_CORRECT_TO_UNLOCK) {
                if(focusFeedbackEl) focusFeedbackEl.innerHTML = `<div class="alert alert-success">Tuyệt vời! Bạn đã trả lời đúng ${questionsCorrect}/${totalAttempted} câu. Mở khóa thành công!</div>`;
                setTimeout(() => { if (focusModal) focusModal.hide(); }, 2500);
            } else {
                if(focusFeedbackEl) focusFeedbackEl.innerHTML = `<div class="alert alert-warning">Bạn đã trả lời đúng ${questionsCorrect}/${totalAttempted} câu. Cần ít nhất ${MIN_CORRECT_TO_UNLOCK} câu đúng để mở khóa.</div>`;
                setTimeout(() => { if (focusModal) focusModal.hide(); }, 4000);
            }
        }

        if (focusLockBtn) {
            focusLockBtn.addEventListener('click', function() {
                startFocusLockSession(false);
                focusModal.show();
            });
        }

        if (checkFocusAnswerBtn) {
            checkFocusAnswerBtn.addEventListener('click', function() {
                if (currentQuestionIndex >= questionsBatch.length) return;
                const questionData = questionsBatch[currentQuestionIndex];
                const isCorrect = checkAnswerSimilarity(focusAnswerInput.value, questionData.a);
                if (isCorrect) {
                    questionsCorrect++;
                    if(focusFeedbackEl) focusFeedbackEl.innerHTML = '<div class="alert alert-success p-1 small">Chính xác!</div>';
                } else {
                    if(focusFeedbackEl) focusFeedbackEl.innerHTML = `<div class="alert alert-danger p-1 small">Sai rồi. Đáp án đúng là: "<strong>${questionData.a}</strong>"</div>`;
                }
                currentQuestionIndex++;
                if(focusAnswerInput) focusAnswerInput.disabled = true;
                if(checkFocusAnswerBtn) checkFocusAnswerBtn.disabled = true;
                setTimeout(() => { displayCurrentQuestion(); }, 2500);
            });
        }

        focusLockModalEl.addEventListener('hide.bs.modal', function() { resetIdleTimer(); });
        focusLockModalEl.addEventListener('hidden.bs.modal', function() {
            if(focusLockIntroTextEl) focusLockIntroTextEl.textContent = "Để tiếp tục, hãy trả lời câu hỏi ôn tập:";
            resetIdleTimer();
        });

        ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart'].forEach(eventName => {
            document.addEventListener(eventName, resetIdleTimer, false);
        });
        resetIdleTimer(); 
    }

    if (workspaceTabs) {
        const tabs = workspaceTabs.querySelectorAll('a.nav-link');
        tabs.forEach(tab => {
            tab.addEventListener('click', function(event) {
                event.preventDefault();
                tabs.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                const targetTab = this.dataset.tabTarget;
                filterDocuments(targetTab);
            });
        });
        const initialActiveTab = workspaceTabs.querySelector('a.nav-link.active');
        if (initialActiveTab) {
            filterDocuments(initialActiveTab.dataset.tabTarget);
        }
    }

    documentRows.forEach(row => {
        const toggleBtn = row.querySelector('.toggle-workspace-btn');
        if (toggleBtn) {
            const isGoalRelated = toggleBtn.dataset.isGoalRelated === 'true';
            if (isGoalRelated) {
                toggleBtn.classList.add('btn-outline-primary');
            } else {
                toggleBtn.classList.add('btn-outline-success');
            }
        }
    });

    document.addEventListener('click', async function(event) {
        const target = event.target.closest('.toggle-workspace-btn');
        if (target) {
            const docId = target.dataset.docId;
            try {
                const response = await fetch(`/document/${docId}/toggle_goal_related`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                });
                const data = await response.json();
                if (response.ok) {
                    const row = target.closest('tr');
                    const isNewGoalRelated = data.is_goal_related;
                    target.dataset.isGoalRelated = isNewGoalRelated;
                    if (row) row.dataset.docType = isNewGoalRelated ? 'goal-related' : 'sandbox';
                    target.classList.remove('btn-outline-primary', 'btn-outline-success');

                    if (isNewGoalRelated) {
                        target.innerHTML = '<i class="bi bi-box-arrow-right"></i> Chuyển Sandbox';
                        target.classList.add('btn-outline-primary');
                    } else {
                        target.innerHTML = '<i class="bi bi-box-arrow-in-left"></i> Chuyển Focus';
                        target.classList.add('btn-outline-success');
                    }
                    if (workspaceTabs) {
                         const currentActiveTab = workspaceTabs.querySelector('a.nav-link.active');
                        if (currentActiveTab) {
                            filterDocuments(currentActiveTab.dataset.tabTarget);
                        }
                    }
                } else {
                    alert(data.error || 'Lỗi khi cập nhật trạng thái tài liệu.');
                }
            } catch (error) {
                console.error('Lỗi khi gửi yêu cầu toggle:', error);
                alert('Lỗi kết nối server.');
            }
        }
    });

    const goalBundleModal = document.getElementById('goalBundleModal');
    if (goalBundleModal) {
        const predefinedBundlesByRole = {
            "AI Expert": [
                [
                    {
                        title: "Thu nhận & Chuyển đổi",
                        description: "Các công đoạn xử lý giọng nói đầu vào",
                        items: [
                            { name: "Speech-to-Text (STT)", desc: "Chuyển đổi âm thanh thành văn bản", color: "pink", icon: "bi bi-mic" },
                            { name: "Noise Reduction", desc: "Giảm nhiễu âm thanh đầu vào", color: "yellow", icon: "bi bi-volume-mute" }
                        ]
                    },
                    {
                        title: "Hiểu & Xử lý ngôn ngữ",
                        description: "Xử lý ngôn ngữ tự nhiên (NLP)",
                        items: [
                            { name: "Natural Language Understanding (NLU)", desc: "Hiểu ý nghĩa câu nói của người dùng", color: "blue", icon: "bi bi-chat-text" },
                            { name: "Intent Recognition", desc: "Xác định mục đích của người nói", color: "blue", icon: "bi bi-lightbulb" },
                            { name: "Entity Extraction", desc: "Trích xuất thông tin quan trọng", color: "yellow", icon: "bi bi-search" }
                        ]
                    },
                    {
                        title: "Tổng hợp & Phản hồi",
                        description: "Các công đoạn tạo phản hồi",
                        items: [
                            { name: "Text-to-Speech (TTS)", desc: "Chuyển đổi văn bản thành giọng nói tự nhiên", color: "green", icon: "bi bi-megaphone" },
                            { name: "Emotion Synthesis", desc: "Thêm cảm xúc vào giọng nói AI", color: "yellow", icon: "bi bi-emoji-sunglasses" }
                        ]
                    }
                ]
            ],
            "Successful Businessman": [
                [
                    {
                        title: "Phân tích Thị trường",
                        description: "Công cụ và phương pháp đánh giá thị trường",
                        items: [
                            { name: "Phân tích SWOT", desc: "Điểm mạnh, điểm yếu, cơ hội, thách thức", color: "pink", icon: "bi bi-graph-up" },
                            { name: "Nghiên cứu Khách hàng", desc: "Hiểu nhu cầu và hành vi của khách hàng", color: "yellow", icon: "bi bi-people" }
                        ]
                    },
                    {
                        title: "Quản lý Tài chính",
                        description: "Kiến thức về tài chính và đầu tư",
                        items: [
                            { name: "Báo cáo tài chính", desc: "Đọc và phân tích báo cáo doanh thu, lợi nhuận", color: "blue", icon: "bi bi-currency-dollar" },
                            { name: "Quản lý dòng tiền", desc: "Tối ưu hóa nguồn tiền ra vào doanh nghiệp", color: "blue", icon: "bi bi-cash-stack" }
                        ]
                    },
                    {
                        title: "Chiến lược Kinh doanh",
                        description: "Xây dựng và thực thi các chiến lược",
                        items: [
                            { name: "Mô hình Canvas", desc: "Công cụ lập kế hoạch kinh doanh chiến lược", color: "green", icon: "bi bi-border-all" },
                            { name: "Thương hiệu", desc: "Xây dựng và phát triển nhận diện thương hiệu", color: "yellow", icon: "bi bi-award" }
                        ]
                    }
                ]
            ],
            "Game Developer": [
                [
                    {
                        title: "Ngôn ngữ Lập trình",
                        description: "Các ngôn ngữ phổ biến trong phát triển game",
                        items: [
                            { name: "C# (Unity)", desc: "Ngôn ngữ chính cho Unity Engine", color: "pink", icon: "bi bi-filetype-cs" },
                            { name: "C++ (Unreal)", desc: "Ngôn ngữ hiệu năng cao cho Unreal Engine", color: "yellow", icon: "bi bi-filetype-cpp" }
                        ]
                    },
                    {
                        title: "Công cụ Phát triển",
                        description: "Các Engine và IDE chính",
                        items: [
                            { name: "Unity Engine", desc: "Nền tảng phát triển game đa nền tảng", color: "blue", icon: "bi bi-unity" },
                            { name: "Unreal Engine", desc: "Engine đồ họa mạnh mẽ cho game AAA", color: "blue", icon: "bi bi-box" }
                        ]
                    },
                    {
                        title: "Thiết kế Game",
                        description: "Nguyên lý tạo ra trải nghiệm game hấp dẫn",
                        items: [
                            { name: "Game Design Document (GDD)", desc: "Tài liệu phác thảo ý tưởng game", color: "green", icon: "bi bi-journal-text" },
                            { name: "Level Design", desc: "Thiết kế cấu trúc và thử thách màn chơi", color: "yellow", icon: "bi bi-map" }
                        ]
                    }
                ]
            ],
            "Teacher": [

                [
                    {
                        title: "Phương pháp Giảng dạy",
                        description: "Các kỹ thuật sư phạm hiệu quả",
                        items: [
                            { name: "Dạy học Dự án", desc: "Học sinh học qua thực hiện dự án", color: "pink", icon: "bi bi-folder-check" },
                            { name: "Học tập Hợp tác", desc: "Học sinh làm việc nhóm để giải quyết vấn đề", color: "yellow", icon: "bi bi-people" }
                        ]
                    },
                    {
                        title: "Quản lý Lớp học",
                        description: "Kỹ năng quản lý hành vi và môi trường học tập",
                        items: [
                            { name: "Kỷ luật Tích cực", desc: "Xây dựng quy tắc và hậu quả mang tính giáo dục", color: "blue", icon: "bi bi-emoji-sunglasses" },
                            { name: "Tạo động lực", desc: "Khuyến khích và duy trì hứng thú học tập", color: "blue", icon: "bi bi-star-fill" }
                        ]
                    },
                    {
                        title: "Đánh giá Học sinh",
                        description: "Phương pháp đánh giá công bằng và hiệu quả",
                        items: [
                            { name: "Đánh giá Định kỳ", desc: "Bài kiểm tra giữa/cuối kỳ", color: "green", icon: "bi bi-pencil-square" },
                            { name: "Đánh giá Liên tục", desc: "Quan sát, đánh giá qua hoạt động hàng ngày", color: "yellow", icon: "bi bi-clipboard-check" }
                        ]
                    }
                ]
            ],
            "Scientist": [
                [
                    {
                        "title": "Nghiên cứu & Thử nghiệm",
                        "description": "Các giai đoạn của quá trình nghiên cứu khoa học",
                        "items": [
                            { "name": "Lên kế hoạch nghiên cứu", "desc": "Thiết kế phương pháp và mục tiêu nghiên cứu", "color": "purple", "icon": "bi bi-clipboard-data" },
                            { "name": "Thực hiện thí nghiệm", "desc": "Tiến hành các thử nghiệm trong môi trường kiểm soát", "color": "orange", "icon": "bi bi-flask" },
                            { "name": "Thu thập dữ liệu", "desc": "Ghi nhận và tổ chức thông tin thu được", "color": "blue", "icon": "bi bi-database" }
                        ]
                    },
                    {
                        "title": "Phân tích & Diễn giải",
                        "description": "Biến dữ liệu thành kiến thức có giá trị",
                        "items": [
                            { "name": "Phân tích thống kê", "desc": "Áp dụng các phương pháp toán học để hiểu dữ liệu", "color": "green", "icon": "bi bi-bar-chart" },
                            { "name": "Diễn giải kết quả", "desc": "Giải thích ý nghĩa của các phát hiện", "color": "red", "icon": "bi bi-lightbulb" },
                            { "name": "Viết báo cáo khoa học", "desc": "Trình bày kết quả và phương pháp nghiên cứu", "color": "pink", "icon": "bi bi-journal-text" }
                        ]
                    },
                    {
                        "title": "Đổi mới & Phát triển",
                        "description": "Đóng góp vào sự tiến bộ của khoa học",
                        "items": [
                            { "name": "Phát triển lý thuyết mới", "desc": "Xây dựng các mô hình giải thích hiện tượng", "color": "teal", "icon": "bi bi-cpu" },
                            { "name": "Ứng dụng khoa học", "desc": "Chuyển đổi kiến thức thành giải pháp thực tiễn", "color": "brown", "icon": "bi bi-tools" }
                        ]
                    }
                ]
            ],
            "Doctor": [
                [
                    {
                        "title": "Khám & Chẩn đoán",
                        "description": "Quy trình xác định tình trạng bệnh lý",
                        "items": [
                            { "name": "Thu thập bệnh sử", "desc": "Tìm hiểu thông tin về tiền sử bệnh của bệnh nhân", "color": "blue", "icon": "bi bi-file-earmark-medical" },
                            { "name": "Khám lâm sàng", "desc": "Kiểm tra thể chất và các triệu chứng", "color": "green", "icon": "bi bi-hospital" },
                            { "name": "Chỉ định xét nghiệm", "desc": "Yêu cầu các xét nghiệm để hỗ trợ chẩn đoán", "color": "yellow", "icon": "bi bi-clipboard" }
                        ]
                    },
                    {
                        "title": "Điều trị & Chăm sóc",
                        "description": "Các phương pháp can thiệp và hỗ trợ bệnh nhân",
                        "items": [
                            { "name": "Lập kế hoạch điều trị", "desc": "Xây dựng phác đồ điều trị phù hợp", "color": "red", "icon": "bi bi-medkit" },
                            { "name": "Kê đơn thuốc", "desc": "Chỉ định thuốc và hướng dẫn sử dụng", "color": "pink", "icon": "bi bi-prescription" },
                            { "name": "Tư vấn sức khỏe", "desc": "Cung cấp lời khuyên để cải thiện sức khỏe", "color": "purple", "icon": "bi bi-heart-pulse" }
                        ]
                    },
                    {
                        "title": "Phòng ngừa & Giáo dục",
                        "description": "Nâng cao sức khỏe cộng đồng",
                        "items": [
                            { "name": "Tiêm chủng & Sàng lọc", "desc": "Thực hiện các biện pháp phòng bệnh", "color": "teal", "icon": "bi bi-shield-check" },
                            { "name": "Giáo dục y tế cộng đồng", "desc": "Nâng cao nhận thức về sức khỏe", "color": "orange", "icon": "bi bi-people" }
                        ]
                    }
                ]
            ],
            "Architect": [
                [
                    {
                        "title": "Thiết kế & Lập kế hoạch",
                        "description": "Quá trình hình thành ý tưởng và phác thảo công trình",
                        "items": [
                            { "name": "Nghiên cứu địa điểm", "desc": "Phân tích đặc điểm môi trường và quy hoạch", "color": "brown", "icon": "bi bi-geo-alt" },
                            { "name": "Lên ý tưởng thiết kế", "desc": "Phát triển các khái niệm kiến trúc", "color": "indigo", "icon": "bi bi-lightbulb" },
                            { "name": "Vẽ bản phác thảo", "desc": "Tạo ra các hình ảnh ban đầu của dự án", "color": "cyan", "icon": "bi bi-pencil-square" }
                        ]
                    },
                    {
                        "title": "Phát triển & Chi tiết",
                        "description": "Biến ý tưởng thành bản vẽ kỹ thuật",
                        "items": [
                            { "name": "Thiết kế kỹ thuật", "desc": "Chi tiết hóa cấu trúc và vật liệu", "color": "red", "icon": "bi bi-rulers" },
                            { "name": "Chọn vật liệu", "desc": "Lựa chọn nguyên liệu phù hợp cho công trình", "color": "green", "icon": "bi bi-bricks" },
                            { "name": "Tuân thủ quy định", "desc": "Đảm bảo thiết kế đáp ứng các tiêu chuẩn xây dựng", "color": "yellow", "icon": "bi bi-clipboard-check" }
                        ]
                    },
                    {
                        "title": "Giám sát & Quản lý",
                        "description": "Đảm bảo quá trình thi công theo đúng thiết kế",
                        "items": [
                            { "name": "Giám sát thi công", "desc": "Theo dõi tiến độ và chất lượng công trình", "color": "blue", "icon": "bi bi-hard-hat" },
                            { "name": "Quản lý dự án", "desc": "Điều phối các bên liên quan để hoàn thành dự án", "color": "orange", "icon": "bi bi-diagram-3" }
                        ]
                    }
                ]
            ],
            "Engineer": [
                [
                    {
                        "title": "Phân tích & Thiết kế",
                        "description": "Giải quyết vấn đề bằng các nguyên lý khoa học và kỹ thuật",
                        "items": [
                            { "name": "Phân tích yêu cầu", "desc": "Xác định các tiêu chí và hạn chế của dự án", "color": "teal", "icon": "bi bi-list-check" },
                            { "name": "Thiết kế hệ thống/sản phẩm", "desc": "Tạo ra các giải pháp kỹ thuật cụ thể", "color": "purple", "icon": "bi bi-gear" },
                            { "name": "Mô phỏng & Thử nghiệm", "desc": "Kiểm tra và đánh giá hiệu suất thiết kế", "color": "pink", "icon": "bi bi-speedometer2" }
                        ]
                    },
                    {
                        "title": "Phát triển & Triển khai",
                        "description": "Biến thiết kế thành hiện thực",
                        "items": [
                            { "name": "Lập trình/Chế tạo", "desc": "Xây dựng hoặc viết mã cho sản phẩm/hệ thống", "color": "green", "icon": "bi bi-code-slash" },
                            { "name": "Triển khai & Vận hành", "desc": "Đưa sản phẩm vào sử dụng và duy trì", "color": "blue", "icon": "bi bi-play-circle" },
                            { "name": "Giải quyết sự cố", "desc": "Khắc phục các vấn đề phát sinh", "color": "red", "icon": "bi bi-tools" }
                        ]
                    },
                    {
                        "title": "Nghiên cứu & Cải tiến",
                        "description": "Nâng cao hiệu quả và tìm kiếm giải pháp mới",
                        "items": [
                            { "name": "Nghiên cứu công nghệ mới", "desc": "Khám phá các tiến bộ kỹ thuật", "color": "yellow", "icon": "bi bi-lightbulb-fill" },
                            { "name": "Cải tiến quy trình", "desc": "Tối ưu hóa các hoạt động sản xuất hoặc vận hành", "color": "orange", "icon": "bi bi-arrow-repeat" }
                        ]
                    }
                ]
            ]
        };

        goalBundleModal.addEventListener('show.bs.modal', function (event) {
            const contentContainer = document.getElementById('goalBundleContent');
            const userRoleModel = document.body.dataset.userRoleModel || ''; 


            contentContainer.innerHTML = `
                <div class="text-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2">AI đang phân tích...</p>
                </div>
            `;

            let toolData = [];
            if (predefinedBundlesByRole[userRoleModel] && predefinedBundlesByRole[userRoleModel].length > 0) {
                toolData = predefinedBundlesByRole[userRoleModel][Math.floor(Math.random() * predefinedBundlesByRole[userRoleModel].length)];
            } else {
                const allBundlesAsFlatArray = Object.values(predefinedBundlesByRole).flat();
                if (allBundlesAsFlatArray.length > 0) {
                    toolData = allBundlesAsFlatArray[Math.floor(Math.random() * allBundlesAsFlatArray.length)];
                } else {
                    toolData = [
                        { title: "Không có dữ liệu", description: "Vui lòng thiết lập hồ sơ để nhận gợi ý.", items: [] }
                    ];
                }
            }

            let htmlContent = `
                <style>
                    .goal-bundle-container {
                        display: flex;
                        gap: 1rem;
                        overflow-x: auto;
                        padding-bottom: 1rem; 
                        flex-wrap: nowrap; 
                    }
                    .goal-bundle-column {
                        flex: 0 0 300px; 
                        background-color: #f8f9fa;
                        border-radius: var(--card-border-radius);
                        padding: 1rem;
                        box-shadow: var(--card-shadow);
                        border-top: 4px solid var(--primary-blue); 
                    }
                    .goal-bundle-column h5 {
                        font-weight: bold;
                        color: var(--primary-blue); 
                        margin-bottom: 0.5rem;
                    }
                    .goal-bundle-column .description {
                        font-size: 0.85em;
                        color: var(--text-muted);
                        margin-bottom: 1rem;
                    }
                    .goal-bundle-item {
                        background-color: white;
                        border-radius: var(--element-border-radius);
                        padding: 0.75rem;
                        margin-bottom: 0.75rem;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                        border: 1px solid #dee2e6;
                    }
                    .goal-bundle-item .item-name {
                        font-weight: 600;
                        margin-bottom: 0.25rem;
                    }
                    .goal-bundle-item .item-desc {
                        font-size: 0.8em;
                        color: var(--text-muted);
                    }
                   
                    .goal-bundle-item.pink { border-left: 5px solid #d63384; }
                    .goal-bundle-item.yellow { border-left: 5px solid #ffc107; }
                    .goal-bundle-item.blue { border-left: 5px solid #0d6efd; }
                    .goal-bundle-item.green { border-left: 5px solid #198754; }
                    .goal-bundle-item .item-icon { margin-right: 5px; color: var(--text-muted); }
                </style>
                <div class="goal-bundle-container">
                    ${toolData.map(column => `
                        <div class="goal-bundle-column">
                            <h5 class="mb-2">${column.title}</h5>
                            <p class="description">${column.description}</p>
                            ${column.items.map(item => `
                                <div class="goal-bundle-item ${item.color}">
                                    <div class="item-name"><i class="${item.icon} item-icon"></i>${item.name}</div>
                                    <div class="item-desc">${item.desc}</div>
                                </div>
                            `).join('')}
                        </div>
                    `).join('')}
                </div>
            `;

            setTimeout(() => {
                contentContainer.innerHTML = htmlContent;
            }, 100);
        });
    }
});