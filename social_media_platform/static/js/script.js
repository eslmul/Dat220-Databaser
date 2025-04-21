document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners for the reply buttons
    const replyButtons = document.querySelectorAll('.reply-button');
    
    replyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const commentId = this.getAttribute('data-comment-id');
            const replyForm = document.getElementById(`reply-form-${commentId}`);
            
            if (replyForm.style.display === 'none' || replyForm.style.display === '') {
                replyForm.style.display = 'block';
                this.textContent = 'Avbryt svar';
            } else {
                replyForm.style.display = 'none';
                this.textContent = 'Svar';
            }
        });
    });
    
    // Add event listeners for delete confirmations
    const deleteButtons = document.querySelectorAll('.delete-button');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Er du sikker på at du vil slette dette? Denne handlingen kan ikke angres.')) {
                e.preventDefault();
            }
        });
    });
    
    // Flash message auto-hide
    const flashMessages = document.querySelectorAll('.flash');
    
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.style.display = 'none';
            }, 500);
        }, 5000);
    });
    
    // Tag selection in multiple select dropdowns
    const tagSelects = document.querySelectorAll('.tag-select');
    
    tagSelects.forEach(select => {
        if (select.multiple) {
            // For multi-select, add a helper display showing selected tags
            const tagDisplay = document.createElement('div');
            tagDisplay.className = 'selected-tags';
            select.parentNode.insertBefore(tagDisplay, select.nextSibling);
            
            select.addEventListener('change', function() {
                // Clear current display
                tagDisplay.innerHTML = '';
                
                // Show selected options
                Array.from(this.selectedOptions).forEach(option => {
                    const tag = document.createElement('span');
                    tag.className = 'tag';
                    tag.textContent = option.textContent;
                    tagDisplay.appendChild(tag);
                });
            });
            
            // Trigger change event to initialize display
            select.dispatchEvent(new Event('change'));
        }
    });
    
    // Toggle visibility for reaction controls
    const reactionButton = document.querySelector('.reaction-toggle');
    if (reactionButton) {
        reactionButton.addEventListener('click', function() {
            const reactionControls = document.querySelector('.reaction-controls');
            reactionControls.classList.toggle('show');
        });
    }
    
    // Preview content as you type in text areas
    const contentTextareas = document.querySelectorAll('.content-textarea');
    contentTextareas.forEach(textarea => {
        const previewContainer = document.querySelector('.content-preview');
        if (previewContainer) {
            textarea.addEventListener('input', function() {
                previewContainer.textContent = this.value;
            });
        }
    });
});