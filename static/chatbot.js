document.addEventListener('DOMContentLoaded', function() {
 const chatForm = document.getElementById('chat-form');
 const chatMessages = document.getElementById('chat-messages');
 const userInput = document.getElementById('user-input');
 let showProceed = false;

 chatForm.addEventListener('submit', function(e) {
     e.preventDefault();
     const message = userInput.value.trim();
     if (message) {
         appendMessage('user', message);
         sendMessage(message);
         userInput.value = '';
     }
 });

 function appendMessage(sender, content) {
     const messageDiv = document.createElement('div');
     messageDiv.classList.add('message', sender);
     
     // Add line breaks and indentation
     const formattedContent = content.replace(/\n/g, '<br>').replace(/^(Total entries:|Entries with|Subject:)/gm, '<br>$1');
     
     messageDiv.innerHTML = formattedContent;
     chatMessages.appendChild(messageDiv);
     chatMessages.scrollTop = chatMessages.scrollHeight;
 }

 function sendMessage(message) {
     fetch('/chat', {
         method: 'POST',
         headers: {
             'Content-Type': 'application/json',
         },
         body: JSON.stringify({message: message}),
     })
     .then(response => response.json())
     .then(data => {
         data.responses.forEach(response => {
             appendMessage('bot', response);
         });
         if (data.show_proceed !== undefined) {
             showProceed = data.show_proceed;
             updateProceedButton();
         }
     })
     .catch(error => {
         console.error('Error:', error);
         appendMessage('bot', 'An error occurred. Please try again.');
     });
 }

 function updateProceedButton() {
     let proceedButton = document.getElementById('proceed-button');
     if (showProceed && !proceedButton) {
         proceedButton = document.createElement('button');
         proceedButton.id = 'proceed-button';
         proceedButton.textContent = 'Proceed';
         proceedButton.classList.add('bg-green-500', 'text-white', 'px-4', 'py-2', 'rounded-lg', 'hover:bg-green-600', 'focus:outline-none', 'focus:ring-2', 'focus:ring-green-500', 'mt-4', 'w-full');
         proceedButton.addEventListener('click', handleProceed);
         chatForm.parentNode.insertBefore(proceedButton, chatForm.nextSibling);
     } else if (!showProceed && proceedButton) {
         proceedButton.remove();
     }
 }

 function handleProceed() {
    const lastMessage = chatMessages.lastElementChild.textContent;
    fetch('/save_template', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({last_message: lastMessage}),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.href = '/edit_template';
        } else {
            appendMessage('bot', 'An error occurred while saving the template. Please try again.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        appendMessage('bot', 'An error occurred while saving the template. Please try again.');
    });
}


 // Initial message from the bot
 sendMessage('start');
});
