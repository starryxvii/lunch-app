document.addEventListener("DOMContentLoaded", () => {
    const options = document.querySelectorAll(".meal-option");

    options.forEach(option => {
        option.addEventListener("click", () => {
            // Remove the active class from all options
            options.forEach(o => o.classList.remove("ring-2", "ring-blue-500", "bg-blue-100"));
            console.log("click");
            // Add the active class to the clicked option
            option.classList.add("ring-2", "ring-blue-500", "bg-blue-100");
        });

        // Ensure that the option with the preselected radio is highlighted
        const input = option.querySelector('input[type="radio"]');
        if (input && input.checked) {
            option.classList.add("ring-2", "ring-blue-500", "bg-blue-100");
        }
    });
});
