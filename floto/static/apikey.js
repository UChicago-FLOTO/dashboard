document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("toggle-secret").addEventListener("click", function () {
        var apiKeyField = document.getElementById("api-key");
        if (apiKeyField.getAttribute('type') === 'password') {
            apiKeyField.setAttribute('type', 'text');
        } else {
            apiKeyField.setAttribute('type', 'password');
        }
    });

    document.getElementById('copy-key').addEventListener('click', function () {
        var apiKeyField = document.getElementById('api-key');
        apiKeyField.select();
        window.navigator.clipboard.writeText(apiKeyField.value).then(_ => {
            alert("Copied API key to clipboard!");
        }).catch(_ => {
            alert("Failed to copy API key.");
        });
    });
});