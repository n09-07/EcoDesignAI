document.addEventListener('DOMContentLoaded', () => {
    const signupForm = document.getElementById('signupForm');
    const loginForm = document.getElementById('loginForm');

    // -------------------------
    // SIGNUP
    // -------------------------
    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(signupForm);
            const data = Object.fromEntries(formData.entries());

            try {
                const res = await fetch('/signup', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });

                const result = await res.json();

                document.getElementById('signupMsg').innerText =
                    result.message || result.error || "Signup completed";

                // Optional redirect after signup
                if (result.redirect) {
                    window.location.href = result.redirect;
                }

            } catch (err) {
                console.error("Signup error:", err);
                document.getElementById('signupMsg').innerText =
                    "Something went wrong during signup";
            }
        });
    }

    // -------------------------
    // LOGIN
    // -------------------------
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(loginForm);
            const data = Object.fromEntries(formData.entries());

            try {
                const res = await fetch('/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });

                const result = await res.json();
                document.getElementById('loginMsg').innerText = result.message || result.error || "Login successful";

                // Redirect to studio after login
                if (result.redirect) {
                    window.location.href = result.redirect;
                }

            } catch (err) {
                console.error("Login error:", err);
                document.getElementById('loginMsg').innerText =
                    "Something went wrong during login";
            }
        });
    }
});