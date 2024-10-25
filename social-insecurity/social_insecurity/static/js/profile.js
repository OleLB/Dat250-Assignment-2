document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("edit-details-button").addEventListener("click", function() {
        switchVisibility();
    });
});

function switchVisibility() {
    const viewDetails = document.querySelector('#edit-details');
    const editDetails = document.querySelector('#view-details');

    viewDetails.style.display = (
        viewDetails.style.display == "block" ? "none" : "block");
    editDetails.style.display = (
        editDetails.style.display == "block" ? "none" : "block");
};