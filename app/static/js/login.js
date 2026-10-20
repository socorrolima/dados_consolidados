// Login via Supabase Auth: o backend nunca vê e-mail/senha, só o JWT que
// a Supabase devolve. Guardamos o JWT em localStorage e mandamos como
// Bearer em toda chamada à nossa API (ver static/js/api.js).
(function () {
  const formulario = document.getElementById("form-login");
  const mensagemErro = document.getElementById("mensagem-erro");

  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    mensagemErro.textContent =
      "Projeto Supabase ainda não configurado (SUPABASE_URL/SUPABASE_ANON_KEY).";
    mensagemErro.hidden = false;
    formulario.querySelector("button").disabled = true;
    return;
  }

  const cliente = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    mensagemErro.hidden = true;

    const email = document.getElementById("email").value;
    const senha = document.getElementById("senha").value;

    const { data, error } = await cliente.auth.signInWithPassword({
      email,
      password: senha,
    });

    if (error) {
      mensagemErro.textContent = "E-mail ou senha inválidos.";
      mensagemErro.hidden = false;
      return;
    }

    localStorage.setItem("access_token", data.session.access_token);
    window.location.href = "/dashboard";
  });
})();
