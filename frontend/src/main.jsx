import React, { useCallback, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { LogOut, PackagePlus, Search, ShieldCheck, ShoppingBag, Store, UserRound } from "lucide-react";
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
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId || signedIn) return undefined;
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
          await api.loginGoogle(credential);
          await refreshSession();
          setNotice("Login realizado com Google.");
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
  }, [refreshSession, signedIn]);

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
      setNotice("Entre com Google para finalizar a compra.");
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
          {!signedIn && <div id="google-button" />}
          {signedIn && (
            <>
              <img src={session.user.picture} alt="" />
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

      {view === "sell" && <SellerStudio session={session} refreshSession={refreshSession} onCreated={() => loadProducts()} />}
      {view === "orders" && <OrderList orders={orders} title="Meus pedidos" />}
      {view === "sales" && <OrderList orders={orders} title="Vendas recebidas" />}
    </main>
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

function SellerStudio({ session, refreshSession, onCreated }) {
  const [seller, setSeller] = useState({ display_name: "", bio: "", city: "", state: "SP", document: "" });
  const [product, setProduct] = useState({ title: "", description: "", category: "", price_cents: 10000, inventory: 1, images: [], materials: [], lead_time_days: 3 });
  const [message, setMessage] = useState("");

  async function saveSeller(event) {
    event.preventDefault();
    await api.upsertSeller(seller);
    await refreshSession();
    setMessage("Perfil de vendedor salvo.");
  }

  async function publish(event) {
    event.preventDefault();
    const payload = { ...product, images: product.images.filter(Boolean), materials: product.materials.filter(Boolean) };
    await api.createProduct(payload);
    setMessage("Produto publicado na vitrine.");
    onCreated();
  }

  if (!session.user) {
    return <section className="panel"><h1>Entre para vender</h1><p>Use Google no topo da página para criar seu perfil de vendedor e publicar seus produtos.</p></section>;
  }

  return (
    <section className="studio">
      <form onSubmit={saveSeller}>
        <h1>Perfil do ateliê</h1>
        <input placeholder="Nome público" value={seller.display_name} onChange={(event) => setSeller({ ...seller, display_name: event.target.value })} />
        <textarea placeholder="Bio do ateliê" value={seller.bio} onChange={(event) => setSeller({ ...seller, bio: event.target.value })} />
        <div className="split">
          <input placeholder="Cidade" value={seller.city} onChange={(event) => setSeller({ ...seller, city: event.target.value })} />
          <input placeholder="UF" maxLength="2" value={seller.state} onChange={(event) => setSeller({ ...seller, state: event.target.value.toUpperCase() })} />
        </div>
        <input placeholder="CPF/CNPJ para validação futura" value={seller.document} onChange={(event) => setSeller({ ...seller, document: event.target.value })} />
        <button><Store size={18} /> Salvar perfil</button>
      </form>

      <form onSubmit={publish}>
        <h1>Novo produto</h1>
        <input placeholder="Título" value={product.title} onChange={(event) => setProduct({ ...product, title: event.target.value })} />
        <textarea placeholder="Descrição" value={product.description} onChange={(event) => setProduct({ ...product, description: event.target.value })} />
        <div className="split">
          <input placeholder="Categoria" value={product.category} onChange={(event) => setProduct({ ...product, category: event.target.value })} />
          <input type="number" min="100" step="100" value={product.price_cents} onChange={(event) => setProduct({ ...product, price_cents: Number(event.target.value) })} />
        </div>
        <div className="split">
          <input type="number" min="0" value={product.inventory} onChange={(event) => setProduct({ ...product, inventory: Number(event.target.value) })} />
          <input type="number" min="0" value={product.lead_time_days} onChange={(event) => setProduct({ ...product, lead_time_days: Number(event.target.value) })} />
        </div>
        <input placeholder="URL da imagem principal" onChange={(event) => setProduct({ ...product, images: [event.target.value] })} />
        <input placeholder="Materiais separados por vírgula" onChange={(event) => setProduct({ ...product, materials: event.target.value.split(",").map((item) => item.trim()) })} />
        <button disabled={!session.seller}><PackagePlus size={18} /> Publicar produto</button>
      </form>
      {message && <p className="notice">{message}</p>}
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
