document.getElementById('uploadForm').addEventListener('submit', function(e) {
 e.preventDefault();
 console.log('Form submitted');
 var formData = new FormData(this);

 fetch('/upload', {
     method: 'POST',
     body: formData
 })
 .then(response => {
     console.log('Response received', response);
     return response.json();
 })
 .then(data => {
     console.log('Data received', data);
     if (data.error) {
         console.error('Error:', data.error);
         document.getElementById('message').textContent = 'Error: ' + data.error;
     } else {
         console.log('Redirecting to /chatbot');
         window.location.href = '/chatbot';
     }
 })
 .catch(error => {
     console.error('Error:', error);
     document.getElementById('message').textContent = 'An error occurred. Please try again.';
 });
});