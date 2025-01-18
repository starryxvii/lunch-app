document.addEventListener("DOMContentLoaded", () => {
    const options = document.querySelectorAll(".meal-option");

    options.forEach(option => {
        option.addEventListener("click", () => {
            // Remove the active class from all options
            options.forEach(o => o.classList.remove("ring-2", "ring-blue-500", "bg-blue-100"));

            // Add the active class to the clicked option
            option.classList.add("ring-2", "ring-blue-500", "bg-blue-100");
        });
    });
});
