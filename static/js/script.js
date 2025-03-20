document.getElementById('symptomForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    // Get the symptoms input
    const symptoms = document.getElementById('symptoms').value.trim();
    if (!symptoms) {
        alert('Please enter your symptoms.');
        return;
    }

    // Show loading spinner and hide results
    const resultsSection = document.getElementById('results');
    const loadingSpinner = document.getElementById('loading');
    const resultContent = document.getElementById('resultContent');
    resultsSection.classList.remove('d-none');
    resultsSection.classList.add('show');
    loadingSpinner.classList.remove('d-none');
    resultContent.style.display = 'none';

    try {
        // Make API call to Flask backend
        const response = await fetch('http://127.0.0.1:5000/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ symptoms }),
        });

        const data = await response.json();

        // Hide loading spinner
        loadingSpinner.classList.add('d-none');
        resultContent.style.display = 'block';

        // Display results
        document.getElementById('disease').textContent = data.predicted_disease || 'N/A';
        document.getElementById('confidence').textContent = data.confidence || 'N/A';
        const confidencePercent = (data.confidence || 0) * 100;
        document.getElementById('confidenceBar').style.width = `${confidencePercent}%`;
        document.getElementById('confidenceBar').setAttribute('aria-valuenow', confidencePercent);

        // Display recommended tests
        const recommendedTests = document.getElementById('recommendedTests');
        recommendedTests.innerHTML = '';
        if (data.recommended_tests && data.recommended_tests.length > 0) {
            data.recommended_tests.forEach(test => {
                const li = document.createElement('li');
                li.classList.add('list-group-item');
                li.innerHTML = `<i class="fas fa-vial me-2 text-primary"></i> ${test}`;
                recommendedTests.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.classList.add('list-group-item');
            li.textContent = 'None';
            recommendedTests.appendChild(li);
        }

        // Display medications
        const medications = document.getElementById('medications');
        medications.innerHTML = '';
        if (data.medications && data.medications.length > 0) {
            data.medications.forEach(med => {
                const li = document.createElement('li');
                li.classList.add('list-group-item');
                li.innerHTML = `<i class="fas fa-pills me-2 text-primary"></i> ${med}`;
                medications.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.classList.add('list-group-item');
            li.textContent = 'None';
            medications.appendChild(li);
        }

        // Dummy additional advice (you can integrate this into your backend later)
        const advice = document.getElementById('advice');
        advice.textContent = data.predicted_disease === 'Common Cold'
            ? 'Rest well, stay hydrated, and consider over-the-counter cold remedies. If symptoms persist, consult a doctor.'
            : 'Follow the recommended tests and consult a healthcare professional for a detailed diagnosis.';
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while fetching the diagnosis. Please try again.');
        loadingSpinner.classList.add('d-none');
        resultsSection.classList.add('d-none');
    }
});

// booking 
document.getElementById('symptomForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const symptoms = document.getElementById('symptoms').value;
    const resultsDiv = document.getElementById('results');
    const loadingDiv = document.getElementById('loading');
    const resultContent = document.getElementById('resultContent');

    // Show loading spinner
    resultsDiv.classList.remove('d-none');
    loadingDiv.classList.remove('d-none');
    resultContent.classList.add('d-none');

    fetch('/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symptoms })
    })
    .then(response => response.json())
    .then(data => {
        loadingDiv.classList.add('d-none');
        resultContent.classList.remove('d-none');

        document.getElementById('disease').textContent = data.predicted_disease;
        document.getElementById('confidence').textContent = `${(data.confidence * 100)}%`;
        document.getElementById('confidenceBar').style.width = `${data.confidence * 100}%`;

        const testsList = document.getElementById('recommendedTests');
        testsList.innerHTML = '';
        data.recommended_tests.forEach(test => {
            const li = document.createElement('li');
            li.classList.add('list-group-item');
            li.textContent = test;
            testsList.appendChild(li);
        });

        const medsList = document.getElementById('medications');
        medsList.innerHTML = '';
        data.medications.forEach(med => {
            const li = document.createElement('li');
            li.classList.add('list-group-item');
            li.textContent = med;
            medsList.appendChild(li);
        });

        document.getElementById('advice').textContent = 'Please consult a doctor for a professional diagnosis.';

        // Populate the test dropdown in the booking modal
        const testSelect = document.getElementById('testName');
        testSelect.innerHTML = '<option value="">Choose a test...</option>';
        data.recommended_tests.forEach(test => {
            const option = document.createElement('option');
            option.value = test;
            option.textContent = test;
            testSelect.appendChild(option);
        });

        // Set the disease name in the hidden input
        document.getElementById('diseaseName').value = data.predicted_disease;
    })
    .catch(error => {
        console.error('Error:', error);
        loadingDiv.classList.add('d-none');
        resultContent.innerHTML = '<p class="text-danger">An error occurred. Please try again.</p>';
    });
});

// Handle booking form submission
document.getElementById('submitBooking').addEventListener('click', function() {
    const patientName = document.getElementById('patientName').value;
    const email = document.getElementById('email').value;
    const phone = document.getElementById('phone').value;
    const testName = document.getElementById('testName').value;
    const slotDate = document.getElementById('slotDate').value;  // YYYY-MM-DD
    const slotTime = document.getElementById('slotTime').value;  // HH:MM
    const disease = document.getElementById('diseaseName').value;

    if (!patientName || !email || !testName || !slotDate || !slotTime) {
        alert('Please fill in all required fields.');
        return;
    }

    fetch('/book_blood_test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            patient_name: patientName,
            email: email,
            phone: phone,
            disease: disease,
            test_name: testName,
            slot_date: slotDate,
            slot_time: slotTime
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error: ' + data.error);
        } else {
            alert(data.message);
            bootstrap.Modal.getInstance(document.getElementById('bookingModal')).hide();
            document.getElementById('bookingForm').reset();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while booking. Please try again.');
    });
});