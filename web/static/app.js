/**
 * ResumeAI - Single Page Application Frontend Script
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const stateNoResume = document.getElementById('state-no-resume');
    const stateResumeExists = document.getElementById('state-resume-exists');
    const activeResumeName = document.getElementById('active-resume-name');
    const resumeSelect = document.getElementById('resume-select');
    const fileUploadInput = document.getElementById('file-upload-input');
    const fileChangeInput = document.getElementById('file-change-input');
    const uploadZone = document.getElementById('upload-zone');
    
    const tailorOverlay = document.getElementById('tailor-overlay');
    const jobDescriptionInput = document.getElementById('job-description-input');
    const charCountVal = document.getElementById('char-count-val');
    const generateBtn = document.getElementById('generate-btn');
    const tailorForm = document.getElementById('tailor-form');
    
    const resumesList = document.getElementById('resumes-list');
    const progressOverlay = document.getElementById('progress-overlay');
    const toastContainer = document.getElementById('toast-container');
    
    // Application State
    let appStatus = {
        has_base_resume: false,
        active_resume: null,
        available_resumes: []
    };

    // -------------------------------------------------------------------------
    // Toast Notifications Helper
    // -------------------------------------------------------------------------
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        let icon = '✦';
        if (type === 'error') icon = '⚠️';
        if (type === 'warning') icon = 'ℹ️';
        if (type === 'success') icon = '✓';
        
        toast.innerHTML = `
            <span class="toast-icon">${icon}</span>
            <div class="toast-content">${message}</div>
            <button class="toast-close">&times;</button>
        `;
        
        // Close event
        toast.querySelector('.toast-close').addEventListener('click', () => {
            toast.remove();
        });
        
        toastContainer.appendChild(toast);
        
        // Auto remove
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // -------------------------------------------------------------------------
    // API status check and UI update
    // -------------------------------------------------------------------------
    async function checkStatus() {
        try {
            const response = await fetch('/api/status');
            if (!response.ok) throw new Error('Failed to retrieve status');
            const data = await response.json();
            
            if (data.success) {
                appStatus.has_base_resume = data.has_base_resume;
                appStatus.active_resume = data.active_resume;
                appStatus.available_resumes = data.available_resumes;
                
                updateUI();
            } else {
                showToast(data.error || 'Status error', 'error');
            }
        } catch (error) {
            console.error(error);
            showToast('Error connecting to backend server.', 'error');
        }
    }

    function updateUI() {
        if (appStatus.has_base_resume) {
            // State 2: Resume Exists
            stateNoResume.classList.add('hidden');
            stateResumeExists.classList.remove('hidden');
            activeResumeName.textContent = appStatus.active_resume;
            
            // Unlock Job Description area
            tailorOverlay.style.opacity = '0';
            setTimeout(() => {
                tailorOverlay.classList.add('hidden');
            }, 300);
            jobDescriptionInput.removeAttribute('disabled');
            generateBtn.removeAttribute('disabled');
            
            // Populate select dropdown
            resumeSelect.innerHTML = '';
            appStatus.available_resumes.forEach(res => {
                const opt = document.createElement('option');
                opt.value = res;
                opt.textContent = res;
                if (res === appStatus.active_resume) {
                    opt.selected = true;
                }
                resumeSelect.appendChild(opt);
            });
        } else {
            // State 1: No Resume Uploaded
            stateNoResume.classList.remove('hidden');
            stateResumeExists.classList.add('hidden');
            
            // Lock Job Description area
            tailorOverlay.classList.remove('hidden');
            setTimeout(() => {
                tailorOverlay.style.opacity = '1';
            }, 50);
            jobDescriptionInput.setAttribute('disabled', 'true');
            generateBtn.setAttribute('disabled', 'true');
        }
    }

    // ---------------------------------------------------------
    // Fetch and display generated resumes
    // ---------------------------------------------------------
    async function loadGeneratedResumes() {
        try {
            const response = await fetch('/api/resumes');
            if (!response.ok) throw new Error('Failed to fetch resumes');
            const data = await response.json();
            
            if (data.success) {
                displayResumesList(data.resumes);
            }
        } catch (error) {
            console.error('Error loading generated resumes:', error);
        }
    }

    function displayResumesList(resumes) {
        if (!resumes || resumes.length === 0) {
            resumesList.innerHTML = `
                <div class="list-empty">
                    <p>No tailored resumes generated yet.</p>
                </div>
            `;
            return;
        }

        resumesList.innerHTML = '';
        resumes.forEach(res => {
            const card = document.createElement('div');
            card.className = 'resume-item-card';
            card.innerHTML = `
                <div class="resume-item-details">
                    <div class="resume-item-title">${res.job_title}</div>
                    <div class="resume-item-file" title="${res.filename}">${res.filename}</div>
                    <div class="resume-item-date">${res.created_at}</div>
                </div>
                <div class="resume-item-action">
                    <a href="/api/download/${encodeURIComponent(res.filename)}" class="btn btn-secondary" download>
                        Download ⇩
                    </a>
                </div>
            `;
            resumesList.appendChild(card);
        });
    }

    // -------------------------------------------------------------------------
    // Resume Ingestion / Upload handlers
    // -------------------------------------------------------------------------
    async function uploadResumeFile(file) {
        if (!file) return;
        if (file.type !== 'application/pdf' && !file.name.endsWith('.pdf')) {
            showToast('Please select a valid PDF file.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        showToast('Uploading base resume and indexing vector store...', 'warning');

        try {
            const response = await fetch('/api/resume/upload', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) throw new Error('Upload error');
            const data = await response.json();

            if (data.success) {
                showToast('✓ Base resume uploaded and indexed successfully.');
                await checkStatus();
            } else {
                showToast(data.error || 'Ingestion failed.', 'error');
            }
        } catch (error) {
            console.error(error);
            showToast('Connection error during upload.', 'error');
        }
    }

    // Connect file inputs
    fileUploadInput.addEventListener('change', (e) => {
        uploadResumeFile(e.target.files[0]);
        fileUploadInput.value = ''; // Reset input
    });

    fileChangeInput.addEventListener('change', (e) => {
        uploadResumeFile(e.target.files[0]);
        fileChangeInput.value = ''; // Reset input
    });

    // -------------------------------------------------------------------------
    // Drag & Drop Handlers
    // -------------------------------------------------------------------------
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadZone.classList.remove('dragover');
        }, false);
    });

    uploadZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            uploadResumeFile(files[0]);
        }
    });

    // -------------------------------------------------------------------------
    // Change Active Base Resume Dropdown Selection
    // -------------------------------------------------------------------------
    resumeSelect.addEventListener('change', async (e) => {
        const filename = e.target.value;
        if (!filename) return;

        showToast(`Switching base resume to: ${filename}...`, 'warning');

        try {
            const response = await fetch('/api/resume/change', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ filename })
            });

            if (!response.ok) throw new Error('Change request failed');
            const data = await response.json();

            if (data.success) {
                showToast(`✓ Base resume updated. Current resume: ${data.active_resume}`);
                await checkStatus();
            } else {
                showToast(data.error || 'Failed to switch base resume.', 'error');
            }
        } catch (error) {
            console.error(error);
            showToast('Connection error while switching base resume.', 'error');
        }
    });

    // -------------------------------------------------------------------------
    // Character Counter
    // -------------------------------------------------------------------------
    jobDescriptionInput.addEventListener('input', (e) => {
        const textLength = e.target.value.length;
        charCountVal.textContent = textLength.toLocaleString();
    });

    // -------------------------------------------------------------------------
    // Progress steps simulation and Generation Trigger
    // -------------------------------------------------------------------------
    function resetProgressSteps() {
        const steps = ['step-1', 'step-2', 'step-3', 'step-4'];
        steps.forEach(id => {
            const el = document.getElementById(id);
            el.className = 'step-item pending';
        });
    }

    function setStepState(stepNumber, state) {
        const el = document.getElementById(`step-${stepNumber}`);
        if (!el) return;
        el.className = `step-item ${state}`;
    }

    tailorForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const jdText = jobDescriptionInput.value.strip ? jobDescriptionInput.value.strip() : jobDescriptionInput.value.trim();
        
        if (!jdText) {
            showToast('Please paste a job description first.', 'error');
            return;
        }

        // Show overlay & reset steps
        resetProgressSteps();
        progressOverlay.classList.remove('hidden');

        // Step-by-step progress timer simulator
        let stepTimers = [];
        
        // Step 1: Active immediately
        setStepState(1, 'active');
        
        // Step 2: after 3 seconds
        stepTimers.push(setTimeout(() => {
            setStepState(1, 'completed');
            setStepState(2, 'active');
        }, 3000));

        // Step 3: after 6 seconds
        stepTimers.push(setTimeout(() => {
            setStepState(2, 'completed');
            setStepState(3, 'active');
        }, 7000));

        // Step 4: after 12 seconds
        stepTimers.push(setTimeout(() => {
            setStepState(3, 'completed');
            setStepState(4, 'active');
        }, 14000));

        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ job_description: jdText })
            });

            const data = await response.json();

            // Clear all step-timers since response is back
            stepTimers.forEach(timer => clearTimeout(timer));

            if (data.success) {
                // Complete all steps immediately
                for (let i = 1; i <= 4; i++) {
                    setStepState(i, 'completed');
                }
                
                showToast('✓ Tailored resume generated successfully.');
                
                // Refresh list of generated resumes
                await loadGeneratedResumes();
                
                // Hide overlay after a brief delay so user sees completion
                setTimeout(() => {
                    progressOverlay.classList.add('hidden');
                    // Reset text input and char count
                    jobDescriptionInput.value = '';
                    charCountVal.textContent = '0';
                }, 1000);
            } else {
                progressOverlay.classList.add('hidden');
                showToast(data.error || 'Generation pipeline failed.', 'error');
            }
        } catch (error) {
            console.error(error);
            stepTimers.forEach(timer => clearTimeout(timer));
            progressOverlay.classList.add('hidden');
            showToast('Connection error during resume generation.', 'error');
        }
    });

    // -------------------------------------------------------------------------
    // Initial Startup Invocation
    // -------------------------------------------------------------------------
    checkStatus();
    loadGeneratedResumes();
});
