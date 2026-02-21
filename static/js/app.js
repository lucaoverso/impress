async function login() {
    const email = document.getElementById("email").value;
    const senha = document.getElementById("senha").value;

    const res = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, senha })
    });

    const data = await res.json();

    if (!res.ok) {
        document.getElementById("erro").innerText = data.detail;
        return;
    }

    localStorage.setItem("token", data.token);

    if (data.perfil === "admin") {
        window.location.href = "/admin";
    } else {
        window.location.href = "/servicos";
    }
}
