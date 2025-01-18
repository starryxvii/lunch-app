document.addEventListener("DOMContentLoaded", () => {
    const ordersTableBody = document.querySelector("#orders-table tbody");

    // Function to fetch and update orders
    const fetchOrders = async () => {
        try {
            const response = await fetch("/api/orders");
            if (!response.ok) throw new Error("Failed to fetch orders");

            const orders = await response.json();
            ordersTableBody.innerHTML = ""; // Clear the table

            // Populate table with new data
            orders.forEach(order => {
                const row = document.createElement("tr");
                row.classList.add("hover:bg-gray-50");

                row.innerHTML = `
                    <td class="px-4 py-2 border">${order.id}</td>
                    <td class="px-4 py-2 border">${order.student_id}</td>
                    <td class="px-4 py-2 border">${order.meal}</td>
                    <td class="px-4 py-2 border">
                        ${order.picked_up 
                            ? '<span class="text-green-600 font-medium">Picked Up</span>'
                            : '<span class="text-red-600 font-medium">Pending</span>'}
                    </td>
                    <td class="px-4 py-2 border">${order.timestamp}</td>
                    <td class="px-4 py-2 border">
                        ${!order.picked_up 
                            ? `<form action="/mark_picked_up" method="POST">
                                    <input type="hidden" name="order_id" value="${order.id}">
                                    <button type="submit" 
                                            class="bg-green-500 text-white py-1 px-3 rounded-lg hover:bg-green-600">
                                        ✅ Mark Picked Up
                                    </button>
                               </form>`
                            : ""}
                    </td>
                `;
                ordersTableBody.appendChild(row);
            });
        } catch (error) {
            console.error("Error fetching orders:", error);
        }
    };

    // Poll the API every 5 seconds
    setInterval(fetchOrders, 5000);
});
