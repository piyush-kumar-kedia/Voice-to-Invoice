import { useEffect, useState } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { FileAudio, Receipt, Package, Menu, X, Download, CreditCard, Plus, Edit2, Trash2, Search, AlertCircle, Users, DollarSign, Home as HomeIcon, ChevronRight, Info } from "lucide-react";
import Home from "./Home";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = () => {
  const [invoices, setInvoices] = useState([]);
  const [stats, setStats] = useState({ total: 0, thisMonth: 0, revenue: 0 });
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchInvoices();
  }, []);

  const fetchInvoices = async () => {
    try {
      const response = await axios.get(`${API}/invoices`);
      const invoiceData = response.data;
      setInvoices(invoiceData);

      // Calculate stats
      const total = invoiceData.length;
      const now = new Date();
      const thisMonth = invoiceData.filter(
        (inv) => new Date(inv.date).getMonth() === now.getMonth()
      ).length;
      const revenue = invoiceData.reduce((sum, inv) => sum + inv.total, 0);

      setStats({ total, thisMonth, revenue });
      setLoading(false);
    } catch (e) {
      console.error("Error fetching invoices:", e);
      setLoading(false);
    }
  };

  const downloadPDF = async (invoiceId, invoiceNumber) => {
    try {
      const response = await axios.get(`${API}/invoices/${invoiceId}/pdf`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `invoice_${invoiceNumber}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Error downloading PDF:', error);
      alert('Failed to download PDF');
    }
  };

  const createPaymentLink = async (invoiceId) => {
    try {
      const response = await axios.post(`${API}/invoices/${invoiceId}/create-payment`);
      if (response.data.success) {
        alert(`Payment link created!\n${response.data.payment_link}`);
        fetchInvoices();
      }
    } catch (error) {
      console.error('Error creating payment link:', error);
      alert('Failed to create payment link');
    }
  };

  const deleteInvoice = async (invoiceId, invoiceNumber) => {
    if (window.confirm(`Are you sure you want to delete invoice ${invoiceNumber}?`)) {
      try {
        await axios.delete(`${API}/invoices/${invoiceId}`);
        alert('Invoice deleted successfully');
        fetchInvoices();
      } catch (error) {
        console.error('Error deleting invoice:', error);
        alert('Failed to delete invoice');
      }
    }
  };

  return (
    <div className="min-h-screen">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="stat-card" data-testid="total-invoices-card">
          <div className="stat-icon">
            <Receipt size={24} />
          </div>
          <div>
            <p className="stat-label">Total Invoices</p>
            <p className="stat-value" data-testid="total-invoices-value">{stats.total}</p>
          </div>
        </div>

        <div className="stat-card" data-testid="monthly-invoices-card">
          <div className="stat-icon">
            <FileAudio size={24} />
          </div>
          <div>
            <p className="stat-label">This Month</p>
            <p className="stat-value" data-testid="monthly-invoices-value">{stats.thisMonth}</p>
          </div>
        </div>

        <div className="stat-card" data-testid="revenue-card">
          <div className="stat-icon">
            <Package size={24} />
          </div>
          <div>
            <p className="stat-label">Total Revenue</p>
            <p className="stat-value" data-testid="revenue-value">₹{stats.revenue.toFixed(2)}</p>
          </div>
        </div>
      </div>

      <div className="invoice-section">
        <h2 className="section-title">Recent Invoices</h2>
        {loading ? (
          <div className="text-center py-12">
            <div className="loading-spinner"></div>
          </div>
        ) : invoices.length === 0 ? (
          <div className="empty-state" data-testid="empty-invoices">
            <Receipt size={48} className="empty-icon" />
            <h3>No invoices yet</h3>
            <p>Send a voice message on WhatsApp to create your first invoice!</p>
          </div>
        ) : (
          <div className="invoice-grid">
            {invoices.slice(0, 10).map((invoice) => (
              <div key={invoice.id} className="invoice-card" data-testid={`invoice-card-${invoice.id}`}>
                <div className="invoice-header">
                  <h3 className="invoice-number" data-testid={`invoice-number-${invoice.id}`}>{invoice.invoice_number}</h3>
                  <span className={`invoice-status status-${invoice.status}`} data-testid={`invoice-status-${invoice.id}`}>
                    {invoice.status}
                  </span>
                </div>
                <div className="invoice-details">
                  <p className="invoice-customer" data-testid={`invoice-customer-${invoice.id}`}>
                    <strong>Customer:</strong> {invoice.customer_name}
                  </p>
                  <p className="invoice-date" data-testid={`invoice-date-${invoice.id}`}>
                    <strong>Date:</strong> {new Date(invoice.date).toLocaleDateString()}
                  </p>
                  <p className="invoice-total" data-testid={`invoice-total-${invoice.id}`}>
                    <strong>Total:</strong> ₹{invoice.total.toFixed(2)}
                  </p>
                  {invoice.amount_due > 0 && (
                    <p className="invoice-due">
                      <strong>Due:</strong> ₹{invoice.amount_due.toFixed(2)}
                    </p>
                  )}
                </div>
                <div className="invoice-items">
                  <p className="items-label">Items:</p>
                  {invoice.items.map((item, idx) => (
                    <p key={idx} className="item-detail" data-testid={`invoice-item-${invoice.id}-${idx}`}>
                      • {item.name} ({item.quantity} × ₹{item.price})
                    </p>
                  ))}
                </div>
                
                <div className="invoice-actions">
                  <button 
                    className="action-btn btn-pdf"
                    onClick={() => downloadPDF(invoice.id, invoice.invoice_number)}
                    data-testid={`download-pdf-${invoice.id}`}
                  >
                    <Download size={16} />
                    PDF
                  </button>
                  
                  {invoice.payment_link && (
                    <a 
                      href={invoice.payment_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="action-btn btn-pay-now"
                      data-testid={`pay-now-${invoice.id}`}
                    >
                      <CreditCard size={16} />
                      Pay Now
                    </a>
                  )}
                  
                  <button 
                    className="action-btn btn-delete"
                    onClick={() => deleteInvoice(invoice.id, invoice.invoice_number)}
                    data-testid={`delete-invoice-${invoice.id}`}
                  >
                    <Trash2 size={16} />
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Due Management Component
const DueManagement = () => {
  const [dueInvoices, setDueInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalDue, setTotalDue] = useState(0);

  useEffect(() => {
    fetchDueInvoices();
  }, []);

  const fetchDueInvoices = async () => {
    try {
      const response = await axios.get(`${API}/invoices`);
      const allInvoices = response.data;
      
      // Filter invoices with pending payments
      const due = allInvoices.filter(inv => 
        inv.status === 'unpaid' || inv.status === 'partial' || inv.amount_due > 0
      );
      
      setDueInvoices(due);
      const total = due.reduce((sum, inv) => sum + inv.amount_due, 0);
      setTotalDue(total);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching due invoices:', error);
      setLoading(false);
    }
  };

  const markAsPaid = async (invoiceId) => {
    if (window.confirm('Mark this invoice as fully paid?')) {
      try {
        // You would call an API endpoint to update the invoice
        await axios.put(`${API}/invoices/${invoiceId}`, {
          status: 'paid',
          amount_paid: 0,
          amount_due: 0
        });
        alert('Invoice marked as paid!');
        fetchDueInvoices();
      } catch (error) {
        console.error('Error marking as paid:', error);
        alert('Failed to update invoice');
      }
    }
  };

  return (
    <div className="due-management">
      <div className="due-header">
        <div className="due-stats-card">
          <AlertCircle size={32} className="due-icon" />
          <div>
            <p className="due-label">Total Pending</p>
            <p className="due-value">₹{totalDue.toFixed(2)}</p>
          </div>
        </div>
        <div className="due-stats-card">
          <Receipt size={32} className="due-icon" />
          <div>
            <p className="due-label">Pending Invoices</p>
            <p className="due-value">{dueInvoices.length}</p>
          </div>
        </div>
      </div>

      <div className="invoice-section">
        <h2 className="section-title">Pending Payments</h2>
        {loading ? (
          <div className="text-center py-12">
            <div className="loading-spinner"></div>
          </div>
        ) : dueInvoices.length === 0 ? (
          <div className="empty-state">
            <DollarSign size={48} className="empty-icon" />
            <h3>No pending payments</h3>
            <p>All invoices are paid! 🎉</p>
          </div>
        ) : (
          <div className="due-table">
            <table>
              <thead>
                <tr>
                  <th>Invoice</th>
                  <th>Customer</th>
                  <th>Date</th>
                  <th>Total</th>
                  <th>Paid</th>
                  <th>Due</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {dueInvoices.map((invoice) => (
                  <tr key={invoice.id}>
                    <td className="invoice-num">{invoice.invoice_number}</td>
                    <td>{invoice.customer_name}</td>
                    <td>{new Date(invoice.date).toLocaleDateString()}</td>
                    <td>₹{invoice.total.toFixed(2)}</td>
                    <td>₹{invoice.amount_paid.toFixed(2)}</td>
                    <td className="amount-due">₹{invoice.amount_due.toFixed(2)}</td>
                    <td>
                      <span className={`status-badge status-${invoice.status}`}>
                        {invoice.status}
                      </span>
                    </td>
                    <td>
                      <div className="table-actions">
                        <button className="action-btn btn-small btn-pdf" title="Download PDF">
                          <Download size={14} />
                        </button>
                        <button 
                          className="action-btn btn-small btn-success"
                          onClick={() => markAsPaid(invoice.id)}
                          title="Mark as Paid"
                        >
                          <CreditCard size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

// Customer Management Component  
const CustomerManagement = () => {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    address: '',
    user_id: 'default-user',
    language: 'en',
    notes: ''
  });

  useEffect(() => {
    fetchCustomers();
  }, []);

  const fetchCustomers = async () => {
    try {
      const response = await axios.get(`${API}/customers`);
      setCustomers(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching customers:', error);
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingCustomer) {
        await axios.put(`${API}/customers/${editingCustomer.id}`, formData);
        alert('Customer updated successfully!');
      } else {
        await axios.post(`${API}/customers`, formData);
        alert('Customer added successfully!');
      }
      setFormData({ name: '', email: '', phone: '', address: '', user_id: 'default-user', language: 'en', notes: '' });
      setShowAddForm(false);
      setEditingCustomer(null);
      fetchCustomers();
    } catch (error) {
      console.error('Error saving customer:', error);
      alert('Failed to save customer');
    }
  };

  const handleEdit = (customer) => {
    setEditingCustomer(customer);
    setFormData({
      name: customer.name,
      email: customer.email || '',
      phone: customer.phone || '',
      address: customer.address || '',
      user_id: customer.user_id,
      language: customer.language || 'en',
      notes: customer.notes || ''
    });
    setShowAddForm(true);
  };

  const handleDelete = async (customerId, customerName) => {
    if (window.confirm(`Are you sure you want to delete ${customerName}?`)) {
      try {
        await axios.delete(`${API}/customers/${customerId}`);
        alert('Customer deleted successfully!');
        fetchCustomers();
      } catch (error) {
        console.error('Error deleting customer:', error);
        alert('Failed to delete customer');
      }
    }
  };

  const filteredCustomers = customers.filter(customer =>
    customer.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (customer.email && customer.email.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (customer.phone && customer.phone.includes(searchQuery))
  );

  return (
    <div className="customer-management">
      <div className="catalog-header">
        <h2 className="section-title">Customer Database</h2>
        <button 
          className="btn-add-product"
          onClick={() => {
            setShowAddForm(!showAddForm);
            if (showAddForm) {
              setEditingCustomer(null);
              setFormData({ name: '', email: '', phone: '', address: '', user_id: 'default-user', language: 'en', notes: '' });
            }
          }}
          data-testid="toggle-customer-form"
        >
          <Plus size={20} />
          {showAddForm ? 'Cancel' : 'Add Customer'}
        </button>
      </div>

      {showAddForm && (
        <div className="product-form customer-form" data-testid="customer-form">
          <h3>{editingCustomer ? 'Edit Customer' : 'Add New Customer'}</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label>Customer Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  required
                  data-testid="customer-name-input"
                  placeholder="Rajesh Kumar"
                />
              </div>
              <div className="form-group">
                <label>Phone</label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => setFormData({...formData, phone: e.target.value})}
                  data-testid="customer-phone-input"
                  placeholder="+919876543210"
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  data-testid="customer-email-input"
                  placeholder="customer@example.com"
                />
              </div>
              <div className="form-group">
                <label>Language</label>
                <select
                  value={formData.language}
                  onChange={(e) => setFormData({...formData, language: e.target.value})}
                  data-testid="customer-language-input"
                >
                  <option value="en">English</option>
                  <option value="hi">Hindi</option>
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Address</label>
              <textarea
                value={formData.address}
                onChange={(e) => setFormData({...formData, address: e.target.value})}
                data-testid="customer-address-input"
                placeholder="Complete address"
                rows="2"
              />
            </div>
            <div className="form-group">
              <label>Notes (Optional)</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                data-testid="customer-notes-input"
                placeholder="Any additional information"
                rows="2"
              />
            </div>
            <button type="submit" className="btn-submit" data-testid="customer-submit">
              {editingCustomer ? 'Update Customer' : 'Add Customer'}
            </button>
          </form>
        </div>
      )}

      <div className="search-bar">
        <Search size={20} />
        <input
          type="text"
          placeholder="Search customers by name, email, or phone..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          data-testid="customer-search"
        />
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="loading-spinner"></div>
        </div>
      ) : filteredCustomers.length === 0 ? (
        <div className="empty-state">
          <Users size={48} className="empty-icon" />
          <h3>No customers yet</h3>
          <p>Add your first customer to start managing customer database</p>
        </div>
      ) : (
        <div className="customers-table">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Total Purchases</th>
                <th>Total Due</th>
                <th>Language</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredCustomers.map((customer) => (
                <tr key={customer.id} data-testid={`customer-row-${customer.id}`}>
                  <td className="customer-name">{customer.name}</td>
                  <td>{customer.email || '-'}</td>
                  <td>{customer.phone || '-'}</td>
                  <td>₹{customer.total_purchases.toFixed(2)}</td>
                  <td className={customer.total_due > 0 ? 'amount-due' : ''}>
                    ₹{customer.total_due.toFixed(2)}
                  </td>
                  <td>{customer.language === 'hi' ? 'Hindi' : 'English'}</td>
                  <td>
                    <div className="table-actions">
                      <button 
                        onClick={() => handleEdit(customer)}
                        className="action-btn btn-small btn-edit"
                        data-testid={`edit-customer-${customer.id}`}
                        title="Edit"
                      >
                        <Edit2 size={14} />
                      </button>
                      <button 
                        onClick={() => handleDelete(customer.id, customer.name)}
                        className="action-btn btn-small btn-delete"
                        data-testid={`delete-customer-${customer.id}`}
                        title="Delete"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// Product Catalog Component
const ProductCatalog = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    price: '',
    description: '',
    user_id: 'default-user'
  });

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await axios.get(`${API}/products`);
      setProducts(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching products:', error);
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingProduct) {
        await axios.put(`${API}/products/${editingProduct.id}`, formData);
      } else {
        await axios.post(`${API}/products`, formData);
      }
      setFormData({ name: '', price: '', description: '', user_id: 'default-user' });
      setShowAddForm(false);
      setEditingProduct(null);
      fetchProducts();
    } catch (error) {
      console.error('Error saving product:', error);
      alert('Failed to save product');
    }
  };

  const handleEdit = (product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      price: product.price,
      description: product.description || '',
      user_id: product.user_id
    });
    setShowAddForm(true);
  };

  const handleDelete = async (productId) => {
    if (window.confirm('Are you sure you want to delete this product?')) {
      try {
        await axios.delete(`${API}/products/${productId}`);
        fetchProducts();
      } catch (error) {
        console.error('Error deleting product:', error);
        alert('Failed to delete product');
      }
    }
  };

  const filteredProducts = products.filter(product =>
    product.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="product-catalog">
      <div className="catalog-header">
        <h2 className="section-title">Product Catalog</h2>
        <button 
          className="btn-add-product"
          onClick={() => {
            setShowAddForm(!showAddForm);
            if (showAddForm) {
              setEditingProduct(null);
              setFormData({ name: '', price: '', description: '', user_id: 'default-user' });
            }
          }}
          data-testid="toggle-product-form"
        >
          <Plus size={20} />
          {showAddForm ? 'Cancel' : 'Add Product'}
        </button>
      </div>

      {showAddForm && (
        <div className="product-form" data-testid="product-form">
          <h3>{editingProduct ? 'Edit Product' : 'Add New Product'}</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Product Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                required
                data-testid="product-name-input"
              />
            </div>
            <div className="form-group">
              <label>Price (₹)</label>
              <input
                type="number"
                step="0.01"
                value={formData.price}
                onChange={(e) => setFormData({...formData, price: e.target.value})}
                required
                data-testid="product-price-input"
              />
            </div>
            <div className="form-group">
              <label>Description (Optional)</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
                data-testid="product-description-input"
              />
            </div>
            <button type="submit" className="btn-submit" data-testid="product-submit">
              {editingProduct ? 'Update Product' : 'Add Product'}
            </button>
          </form>
        </div>
      )}

      <div className="search-bar">
        <Search size={20} />
        <input
          type="text"
          placeholder="Search products..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          data-testid="product-search"
        />
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="loading-spinner"></div>
        </div>
      ) : filteredProducts.length === 0 ? (
        <div className="empty-state">
          <Package size={48} className="empty-icon" />
          <h3>No products yet</h3>
          <p>Add your first product to start building your catalog</p>
        </div>
      ) : (
        <div className="products-grid">
          {filteredProducts.map((product) => (
            <div key={product.id} className="product-card" data-testid={`product-card-${product.id}`}>
              <div className="product-header">
                <h3 className="product-name">{product.name}</h3>
                <div className="product-actions">
                  <button onClick={() => handleEdit(product)} data-testid={`edit-product-${product.id}`}>
                    <Edit2 size={16} />
                  </button>
                  <button onClick={() => handleDelete(product.id)} data-testid={`delete-product-${product.id}`}>
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              <p className="product-price">₹{product.price.toFixed(2)}</p>
              {product.description && (
                <p className="product-description">{product.description}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const Home = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-content">
          <div className="logo" data-testid="voicebill-logo">
            <FileAudio size={32} className="logo-icon" />
            <div>
              <h1 className="logo-title">VoiceBill</h1>
              <p className="logo-subtitle">Billing on WhatsApp</p>
            </div>
          </div>

          <button
            className="mobile-menu-btn"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            data-testid="mobile-menu-button"
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>

          <nav className="desktop-nav">
            <a href="#features" className="nav-link" data-testid="features-link">Features</a>
            <a href="#how-it-works" className="nav-link" data-testid="how-it-works-link">How it Works</a>
            <Link to="/dashboard" className="nav-link-primary" data-testid="dashboard-link">
              Dashboard
            </Link>
          </nav>
        </div>

        {mobileMenuOpen && (
          <nav className="mobile-nav" data-testid="mobile-nav">
            <a href="#features" className="mobile-nav-link">Features</a>
            <a href="#how-it-works" className="mobile-nav-link">How it Works</a>
            <Link to="/dashboard" className="mobile-nav-link">Dashboard</Link>
            <Link to="/products" className="mobile-nav-link">Products</Link>
          </nav>
        )}
      </header>

      <section className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title" data-testid="hero-title">
            Voice Message to
            <span className="hero-gradient"> Invoice </span>
            in Seconds
          </h1>
          <p className="hero-description" data-testid="hero-description">
            Shopkeepers send a voice note on WhatsApp → Get an automated invoice with UPI payment instantly.
            Perfect for micro-sellers across Bharat and GCC.
          </p>
          <div className="hero-cta">
            <a href="#how-it-works" className="btn-primary" data-testid="get-started-btn">
              Get Started
            </a>
            <Link to="/dashboard" className="btn-secondary" data-testid="view-demo-btn">
              View Demo
            </Link>
          </div>
        </div>
        <div className="hero-visual">
          <div className="floating-card card-1">
            <FileAudio size={40} />
            <p>Voice Note</p>
          </div>
          <div className="floating-card card-2">
            <Receipt size={40} />
            <p>Invoice + Payment</p>
          </div>
        </div>
      </section>

      <section id="features" className="features-section">
        <h2 className="section-heading" data-testid="features-heading">Why VoiceBill?</h2>
        <div className="features-grid">
          <div className="feature-card" data-testid="feature-voice-to-invoice">
            <div className="feature-icon">
              <FileAudio size={32} />
            </div>
            <h3>Voice to Invoice</h3>
            <p>Simply speak your sales details. Our AI converts it to a professional invoice with payment link.</p>
          </div>

          <div className="feature-card" data-testid="feature-whatsapp-native">
            <div className="feature-icon">
              <CreditCard size={32} />
            </div>
            <h3>Instant UPI Payments</h3>
            <p>Get paid instantly via UPI, cards, net banking. Payment link included in every invoice.</p>
          </div>

          <div className="feature-card" data-testid="feature-instant-delivery">
            <div className="feature-icon">
              <Package size={32} />
            </div>
            <h3>Product Catalog</h3>
            <p>Save your products with prices. Voice notes become even faster with pre-saved items.</p>
          </div>
        </div>
      </section>

      <section id="how-it-works" className="how-section">
        <h2 className="section-heading" data-testid="how-it-works-heading">How It Works</h2>
        <div className="steps-container">
          <div className="step" data-testid="step-1">
            <div className="step-number">1</div>
            <h3>Send Voice Note</h3>
            <p>Send a voice message on WhatsApp describing your sale: items, quantities, prices.</p>
          </div>

          <div className="step-arrow">→</div>

          <div className="step" data-testid="step-2">
            <div className="step-number">2</div>
            <h3>AI Processing</h3>
            <p>AI transcribes and extracts billing information. Creates UPI payment link automatically.</p>
          </div>

          <div className="step-arrow">→</div>

          <div className="step" data-testid="step-3">
            <div className="step-number">3</div>
            <h3>Get Invoice + Payment</h3>
            <p>Receive formatted invoice with payment link instantly. Download PDF anytime.</p>
          </div>
        </div>
      </section>

      <section className="cta-section">
        <div className="cta-content">
          <h2 className="cta-title" data-testid="cta-title">Ready to Transform Your Billing?</h2>
          <p className="cta-description">Join thousands of micro-sellers using VoiceBill</p>
          <a href="https://wa.me/14155238886?text=help" className="btn-cta" data-testid="start-free-btn">
            Start Free on WhatsApp
          </a>
        </div>
      </section>

      <footer className="app-footer">
        <p>© 2025 VoiceBill. Built for micro-sellers across Bharat and GCC.</p>
      </footer>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dashboard" element={
            <div className="dashboard-container">
              <div className="dashboard-header">
                <Link to="/" className="back-link" data-testid="back-to-home">
                  ← Back to Home
                </Link>
                <h1 className="dashboard-title">Dashboard</h1>
                <div className="dashboard-nav">
                  <Link to="/due" className="nav-link-secondary" data-testid="due-link">
                    <AlertCircle size={18} />
                    Due Payments
                  </Link>
                  <Link to="/customers" className="nav-link-secondary" data-testid="customers-link">
                    <Users size={18} />
                    Customers
                  </Link>
                  <Link to="/products" className="nav-link-primary" data-testid="products-link">
                    <Package size={18} />
                    Products
                  </Link>
                </div>
              </div>
              <Dashboard />
            </div>
          } />
          <Route path="/due" element={
            <div className="dashboard-container">
              <div className="dashboard-header">
                <Link to="/dashboard" className="back-link" data-testid="back-to-dashboard">
                  ← Back to Dashboard
                </Link>
                <h1 className="dashboard-title">Due Payments</h1>
              </div>
              <DueManagement />
            </div>
          } />
          <Route path="/customers" element={
            <div className="dashboard-container">
              <div className="dashboard-header">
                <Link to="/dashboard" className="back-link" data-testid="back-to-dashboard">
                  ← Back to Dashboard
                </Link>
                <h1 className="dashboard-title">Customer Management</h1>
              </div>
              <CustomerManagement />
            </div>
          } />
          <Route path="/products" element={
            <div className="dashboard-container">
              <div className="dashboard-header">
                <Link to="/dashboard" className="back-link" data-testid="back-to-dashboard">
                  ← Back to Dashboard
                </Link>
                <h1 className="dashboard-title">Product Catalog</h1>
              </div>
              <ProductCatalog />
            </div>
          } />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;