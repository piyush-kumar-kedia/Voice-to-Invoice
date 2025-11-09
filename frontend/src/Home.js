import { Link } from "react-router-dom";
import { FileAudio, Users, Package, Receipt, ArrowRight, Phone, Mail, HelpCircle } from "lucide-react";
import "@/App.css";

const Home = () => {
  return (
    <div className="home-container">
      {/* Hero Section */}
      <div className="hero-section">
        <div className="hero-content">
          <div className="hero-logo">
            <FileAudio size={64} strokeWidth={2} />
          </div>
          <h1 className="hero-title">
            VoiceBill
            <span className="hero-subtitle-hindi">आवाज से बिल बनाएं</span>
          </h1>
          <p className="hero-description">
            WhatsApp पर आवाज भेजें, तुरंत बिल बनाएं
            <br />
            <span className="hero-description-en">Send voice on WhatsApp, Create bills instantly</span>
          </p>
          <Link to="/dashboard" className="hero-cta">
            <span>शुरू करें / Get Started</span>
            <ArrowRight size={20} />
          </Link>
        </div>
      </div>
 {/* How It Works Section */}
  <div className="how-it-works">
    <div className="section-header">
      <h2 className="section-title">कैसे काम करता है?</h2>
      <h2 className="section-title">How It Works</h2>
    </div>

   <div className="features-grid" style={{ marginLeft: "10px", marginRight: "10px" }}>
      <div className="feature-card">
        <Phone size={48} />
        <h3>आवाज भेजें</h3>
        <p>WhatsApp पर आवाज में बोलें:</p>
        <div className="example-box">"राम को 2 चावल बेचा"</div>
        <p className="or-text">या</p>
        <div className="example-box">"sold 2 rice to ram"</div>
      </div>

      <div className="feature-card">
        <Receipt size={48} />
        <h3>बिल बनेगा</h3>
        <p>अपने आप बिल बन जाएगा</p>
        <p>ग्राहक का नाम, सामान, दाम</p>
        <p>सब लिख जाएगा</p>
      </div>

      <div className="feature-card">
        <Mail size={48} />
        <h3>ईमेल मिलेगा</h3>
        <p>ग्राहक को बिल की PDF</p>
        <p>ईमेल से भेज दी जाएगी</p>
        <p>पेमेंट लिंक भी रहेगा</p>
      </div>
    </div>
  </div>

      {/* Features Section */}
      <div className="features-section">
        <h2 className="section-title">
          सुविधाएं / Features
        </h2>
        
        <div className="features-grid">
          <Link to="/dashboard" className="feature-card">
            <Receipt size={32} />
            <h3>बिल देखें</h3>
            <p>सभी बिल एक जगह</p>
            <p className="feature-subtitle">View Invoices</p>
          </Link>

          <Link to="/customers" className="feature-card">
            <Users size={32} />
            <h3>ग्राहक</h3>
            <p>ग्राहकों की जानकारी</p>
            <p className="feature-subtitle">Customers</p>
          </Link>

          <Link to="/products" className="feature-card">
            <Package size={32} />
            <h3>सामान</h3>
            <p>सामान की लिस्ट</p>
            <p className="feature-subtitle">Products</p>
          </Link>

          <Link to="/due" className="feature-card">
            <Receipt size={32} />
            <h3>बकाया</h3>
            <p>जो पैसे बाकी हैं</p>
            <p className="feature-subtitle">Pending Payments</p>
          </Link>
        </div>
      </div>

      {/* Help Section */}
    <div className="help-section-full">
    <div className="section-header">
      <h2 className="section-title">मदद चाहिए?</h2>
      <p className="section-title-en">Need Help?</p>
    </div>

    <div className="features-grid help-grid-centered">
      <div className="feature-card help-card">
        <HelpCircle size={42} />
        <h3>WhatsApp नंबर</h3>
        <div className="help-number">+1 415 523 8886</div>
        <p>पहले "join" लिखकर भेजें</p>
        <p>फिर आवाज भेजें</p>
      </div>
    </div>
  </div>
    </div>
  );
};

export default Home;
