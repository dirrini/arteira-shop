import React, { useCallback, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { LogIn, LogOut, PackagePlus, Search, ShieldCheck, ShoppingBag, Store, UserRound, X } from "lucide-react";
import { api } from "./lib/api";
import "./styles.css";

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

function App() {
  const [session, setSession] = useState({ user: null, seller: null });
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [query, setQuery] = useState("");
  const [view, setView] = useState("market");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [authOpen, setAuthOpen] = useState(false);

  const signedIn = Boolean(session.user);

  const refreshSession = useCallback(async () => {
    try {
      setSession(await api.me());
    } catch {
      setSession({ user: null, seller: null });
    }
  }, []);

  const loadProducts = useCallback(async (q = "") => {
    const data = await api.products(q ? { q } : {});
    setProducts(data.products);
  }, []);

  const loadOrders = useCallback(async () => {
    if (!signedIn) return;
    const role = view === "sales" ? "seller" : "buyer";
    const data = await api.orders(role);
    setOrders(data.orders);
  }, [signedIn, view]);

  useEffect(() => {
    Promise.all([refreshSession(), loadProducts()]).finally(() => setLoading(false));
  }, [refreshSession, loadProducts]);

  useEffect(() => {
    if (view === "orders" || view === "sales") loadOrders();
  }, [view, loadOrders]);

  useEffect(() => {
    if (!authOpen) return undefined;
    const closeOnEscape = (event) => {
      if (event.key === "Escape") setAuthOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [authOpen]);

  const stats = useMemo(() => {
    const active = products.length;
    const artisans = new Set(products.map((item) => item.seller_id)).size;
    return { active, artisans };
  }, [products]);

  async function handleSearch(event) {
    event.preventDefault();
    await loadProducts(query);
  }

  async function buy(product) {
    if (!signedIn) {
      setNotice("Entre ou crie sua conta para finalizar a compra.");
      setAuthOpen(true);
      return;
    }
    const data = await api.checkout({ product_id: product.id, quantity: 1 });
    window.location.href = data.checkout_url;
  }

  async function logout() {
    await api.logout();
    setSession({ user: null, seller: null });
    setView("market");
  }

  return (
    <main>
      <header className="topbar">
        <button className="brand" onClick={() => setView("market")} aria-label="Arteira">
          <span>Arteira</span>
        </button>
        <nav>
          <button className={view === "market" ? "active" : ""} onClick={() => setView("market")}><ShoppingBag size={18} /> Comprar</button>
          <button className={view === "sell" ? "active" : ""} onClick={() => setView("sell")}><Store size={18} /> Vender</button>
          {signedIn && <button className={view === "orders" ? "active" : ""} onClick={() => setView("orders")}><UserRound size={18} /> Pedidos</button>}
          {session.seller && <button className={view === "sales" ? "active" : ""} onClick={() => setView("sales")}><ShieldCheck size={18} /> Vendas</button>}
        </nav>
        <div className="account">
          {!signedIn && (
            <button className="sign-in" onClick={() => setAuthOpen(true)}>
              <LogIn size={18} /> Entrar
            </button>
          )}
          {signedIn && (
            <>
              {session.user.picture ? (
                <img src={session.user.picture} alt="" />
              ) : (
                <span className="account-avatar"><UserRound size={18} /></span>
              )}
              <span>{session.user.name}</span>
              <button className="icon" onClick={logout} aria-label="Sair"><LogOut size={18} /></button>
            </>
          )}
        </div>
      </header>

      {notice && <p className="notice">{notice}</p>}

      {view === "market" && (
        <>
          <section className="hero">
            <div>
              <h1>Arte brasileira feita em pequena escala</h1>
              <p>Compre diretamente de artesãos independentes, com pagamento seguro em reais e curadoria para peças autorais.</p>
            </div>
            <form className="search" onSubmit={handleSearch}>
              <Search size={18} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar cerâmica, bordado, madeira..." />
              <button>Buscar</button>
            </form>
            <dl>
              <div><dt>{stats.active}</dt><dd>peças disponíveis</dd></div>
              <div><dt>{stats.artisans}</dt><dd>ateliês ativos</dd></div>
            </dl>
          </section>
          <ProductGrid loading={loading} products={products} onBuy={buy} />
        </>
      )}

      {view === "sell" && <SellerStudio session={session} refreshSession={refreshSession} onCreated={() => loadProducts()} onSignIn={() => setAuthOpen(true)} />}
      {view === "orders" && <OrderList orders={orders} title="Meus pedidos" />}
      {view === "sales" && <OrderList orders={orders} title="Vendas recebidas" />}

      {authOpen && (
        <AuthDialog
          onClose={() => setAuthOpen(false)}
          onAuthenticated={async (message) => {
            await refreshSession();
            setAuthOpen(false);
            setNotice(message);
          }}
        />
      )}
    </main>
  );
}

function AuthDialog({ onClose, onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
  const googleEnabled = Boolean(clientId && !clientId.startsWith("replace-with"));

  useEffect(() => {
    if (!googleEnabled) return undefined;
    let attempts = 0;
    const renderGoogleButton = () => {
      const target = document.getElementById("google-button");
      if (!target) return;
      if (!window.google) {
        attempts += 1;
        if (attempts < 40) window.setTimeout(renderGoogleButton, 150);
        return;
      }
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async ({ credential }) => {
          try {
            setError("");
            await api.loginGoogle(credential);
            await onAuthenticated("Login realizado com Google.");
          } catch (requestError) {
            setError(requestError.message);
          }
        },
      });
      target.innerHTML = "";
      window.google.accounts.id.renderButton(target, {
        theme: "outline",
        size: "large",
        shape: "rectangular",
        text: "continue_with",
        locale: "pt-BR",
      });
    };
    renderGoogleButton();
    return undefined;
  }, [clientId, googleEnabled, onAuthenticated]);

  function changeMode(nextMode) {
    setMode(nextMode);
    setError("");
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      if (mode === "register") {
        await api.register(form);
        await onAuthenticated("Conta criada com sucesso.");
      } else {
        await api.login({ email: form.email, password: form.password });
        await onAuthenticated("Login realizado com sucesso.");
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="auth-title" onMouseDown={(event) => event.stopPropagation()}>
        <button className="icon close-dialog" onClick={onClose} aria-label="Fechar">
          <X size={20} />
        </button>
        <div className="auth-mark"><UserRound size={24} /></div>
        <h1 id="auth-title">Sua conta Arteira</h1>
        <div className="auth-tabs" role="tablist" aria-label="Acesso à conta">
          <button type="button" role="tab" aria-selected={mode === "login"} className={mode === "login" ? "active" : ""} onClick={() => changeMode("login")}>Entrar</button>
          <button type="button" role="tab" aria-selected={mode === "register"} className={mode === "register" ? "active" : ""} onClick={() => changeMode("register")}>Criar conta</button>
        </div>
        <form className="auth-form" onSubmit={submit}>
          {mode === "register" && (
            <label>
              Nome
              <input required minLength="2" maxLength="80" autoComplete="name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
            </label>
          )}
          <label>
            E-mail
            <input required type="email" autoComplete="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
          </label>
          <label>
            Senha
            <input required type="password" minLength={mode === "register" ? 8 : 1} maxLength="128" autoComplete={mode === "register" ? "new-password" : "current-password"} value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
          </label>
          {mode === "register" && <small>Use pelo menos 8 caracteres.</small>}
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="auth-submit" disabled={submitting}>
            {submitting ? "Aguarde..." : mode === "register" ? "Criar minha conta" : "Entrar"}
          </button>
        </form>
        {googleEnabled && (
          <>
            <div className="auth-divider"><span>ou</span></div>
            <div id="google-button" className="google-button" />
          </>
        )}
      </section>
    </div>
  );
}

function ProductGrid({ loading, products, onBuy }) {
  if (loading) return <section className="grid"><div className="empty">Carregando vitrine...</div></section>;
  if (!products.length) return <section className="grid"><div className="empty">Nenhum produto publicado ainda.</div></section>;
  return (
    <section className="grid">
      {products.map((product) => (
        <article className="product" key={product.id}>
          <img src={product.images?.[0] || "https://images.unsplash.com/photo-1452860606245-08befc0ff44b?auto=format&fit=crop&w=900&q=80"} alt="" />
          <div>
            <p>{product.category}</p>
            <h2>{product.title}</h2>
            <span>{money.format(product.price_cents / 100)}</span>
            <button onClick={() => onBuy(product)}>Comprar</button>
          </div>
        </article>
      ))}
    </section>
  );
}

function SellerStudio({ session, refreshSession, onCreated, onSignIn }) {
  const [seller, setSeller] = useState(() => ({
    display_name: session.seller?.display_name || "",
    bio: session.seller?.bio || "",
    city: session.seller?.city || "",
    state: session.seller?.state || "SP",
    document: session.seller?.document || "",
  }));
  const [product, setProduct] = useState({ title: "", description: "", category: "", price_reais: "100.00", inventory: 1, images: [], materials: [], lead_time_days: 3 });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [savingSeller, setSavingSeller] = useState(false);
  const [publishing, setPublishing] = useState(false);

  function requestErrorMessage(requestError) {
    const fields = requestError.payload?.fields;
    if (fields) {
      const labels = { display_name: "Nome público", city: "Cidade", state: "UF", title: "Título", description: "Descrição", category: "Categoria", price_cents: "Preço", inventory: "Estoque", images: "Imagem", lead_time_days: "Prazo" };
      return Object.entries(fields).map(([field, messages]) => `${labels[field] || field}: ${messages.join(" ")}`).join(" ");
    }
    return requestError.message || "Não foi possível concluir a operação.";
  }

  async function saveSeller(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setSavingSeller(true);
    try {
      await api.upsertSeller(seller);
      await refreshSession();
      setMessage("Perfil de vendedor salvo. Você já pode publicar produtos.");
    } catch (requestError) {
      setError(requestErrorMessage(requestError));
    } finally {
      setSavingSeller(false);
    }
  }

  async function publish(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (!session.seller) {
      setError("Salve um perfil de vendedor válido antes de publicar o produto.");
      return;
    }
    setPublishing(true);
    try {
      const { price_reais: priceReais, ...productFields } = product;
      const payload = {
        ...productFields,
        price_cents: Math.round(Number(String(priceReais).replace(",", ".")) * 100),
        images: product.images.filter(Boolean),
        materials: product.materials.filter(Boolean),
      };
      await api.createProduct(payload);
      setProduct({ title: "", description: "", category: "", price_reais: "100.00", inventory: 1, images: [], materials: [], lead_time_days: 3 });
      setMessage("Produto publicado na vitrine.");
      await onCreated();
    } catch (requestError) {
      setError(requestErrorMessage(requestError));
    } finally {
      setPublishing(false);
    }
  }

  if (!session.user) {
    return (
      <section className="panel sign-in-panel">
        <h1>Entre para vender</h1>
        <p>Crie sua conta para montar o perfil do ateliê e publicar seus produtos.</p>
        <button onClick={onSignIn}><LogIn size={18} /> Entrar com Google</button>
      </section>
    );
  }

  return (
    <section className="studio">
      <form onSubmit={saveSeller}>
        <h1>Perfil do ateliê</h1>
        <label>Nome público<input required minLength="2" maxLength="80" placeholder="Ex.: Ateliê Aurora" value={seller.display_name} onChange={(event) => setSeller({ ...seller, display_name: event.target.value })} /></label>
        <label>Sobre o ateliê<textarea maxLength="1000" placeholder="Conte um pouco sobre seu trabalho" value={seller.bio} onChange={(event) => setSeller({ ...seller, bio: event.target.value })} /></label>
        <div className="split">
          <label>Cidade<input required minLength="2" maxLength="80" placeholder="São Paulo" value={seller.city} onChange={(event) => setSeller({ ...seller, city: event.target.value })} /></label>
          <label>UF<input required minLength="2" maxLength="2" placeholder="SP" value={seller.state} onChange={(event) => setSeller({ ...seller, state: event.target.value.toUpperCase() })} /></label>
        </div>
        <label>CPF/CNPJ <span className="optional">Opcional</span><input maxLength="32" placeholder="Documento para validação futura" value={seller.document} onChange={(event) => setSeller({ ...seller, document: event.target.value })} /></label>
        <button disabled={savingSeller}><Store size={18} /> {savingSeller ? "Salvando..." : "Salvar perfil"}</button>
      </form>

      <form onSubmit={publish}>
        <h1>Novo produto</h1>
        {!session.seller && <p className="form-hint">Salve o perfil do ateliê ao lado para habilitar a publicação.</p>}
        <label>Título<input required minLength="3" maxLength="120" placeholder="Ex.: Vaso de cerâmica artesanal" value={product.title} onChange={(event) => setProduct({ ...product, title: event.target.value })} /></label>
        <label>Descrição<textarea required minLength="10" maxLength="3000" placeholder="Descreva medidas, acabamento e detalhes da peça" value={product.description} onChange={(event) => setProduct({ ...product, description: event.target.value })} /></label>
        <div className="split">
          <label>Categoria<input required minLength="2" maxLength="60" placeholder="Cerâmica" value={product.category} onChange={(event) => setProduct({ ...product, category: event.target.value })} /></label>
          <label>Preço (R$)<input required type="number" min="1" step="0.01" inputMode="decimal" value={product.price_reais} onChange={(event) => setProduct({ ...product, price_reais: event.target.value })} /></label>
        </div>
        <div className="split">
          <label>Estoque<input required type="number" min="0" value={product.inventory} onChange={(event) => setProduct({ ...product, inventory: Number(event.target.value) })} /></label>
          <label>Produção (dias)<input required type="number" min="0" value={product.lead_time_days} onChange={(event) => setProduct({ ...product, lead_time_days: Number(event.target.value) })} /></label>
        </div>
        <label>Imagem principal <span className="optional">Opcional</span><input type="url" placeholder="https://..." value={product.images[0] || ""} onChange={(event) => setProduct({ ...product, images: [event.target.value] })} /></label>
        <label>Materiais <span className="optional">Opcional</span><input placeholder="Argila, esmalte, madeira" value={product.materials.join(", ")} onChange={(event) => setProduct({ ...product, materials: event.target.value.split(",").map((item) => item.trim()) })} /></label>
        <button disabled={publishing}><PackagePlus size={18} /> {publishing ? "Publicando..." : "Publicar produto"}</button>
      </form>
      {message && <p className="notice studio-feedback">{message}</p>}
      {error && <p className="form-error studio-feedback" role="alert">{error}</p>}
    </section>
  );
}

function OrderList({ orders, title }) {
  return (
    <section className="panel">
      <h1>{title}</h1>
      {!orders.length && <p>Nenhum pedido encontrado.</p>}
      {orders.map((order) => (
        <article className="order" key={order.id}>
          <strong>{order.product_snapshot.title}</strong>
          <span>{money.format(order.total_cents / 100)}</span>
          <span>{order.status}</span>
        </article>
      ))}
    </section>
  );
}

createRoot(document.getElementById("root")).render(<App />);
