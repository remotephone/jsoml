document.addEventListener('DOMContentLoaded', function () {
    const optionsCheckboxes = document.querySelectorAll('input[name="options"]')
    const inputData = document.querySelector('#inputData') // Assuming the ID of the input box is 'inputData'
  
    optionsCheckboxes.forEach((checkbox) => {
      checkbox.addEventListener('change', convert)
    })
  
    // Add an event listener for the 'input' event to detect changes in the inputData content
    inputData.addEventListener('input', convert)
  })
  
  function convert() {
    const options = {
      input_box_content: document.getElementById('inputData').value,
      domain_name: document.getElementById('domainName').value, // Retrieve the domain name from the input field
      traefikHTTP: document.getElementById('traefikHTTP').checked,
      traefikHTTPS: document.getElementById('traefikHTTPS').checked,
      traefikNoAuth: document.getElementById('traefikNoAuth').checked,
      volume: document.getElementById('volume').checked,
      volumeNFS: document.getElementById('volumeNFS').checked
    }
    fetch('/traefik_cop_work', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        options: options
      })
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to convert. Please ensure the input is valid YAML.')
        }
        return response.json()
      })
      .then((data) => {
        console.log(data) // Debugging line to see what data is returned
        if (data.output_data !== undefined) {
          document.getElementById('outputData').value = data.output_data
        } else {
          console.error('output_data property is missing in the response')
          document.getElementById('outputData').value = 'Conversion failed. The server response did not include the expected output_data.'
        }
      })
      .catch((error) => {
        console.error('Error:', error)
        document.getElementById('outputData').value = 'Conversion failed. Please ensure the input is valid YAML.'
      })
  }