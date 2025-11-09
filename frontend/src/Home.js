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
        <h2 className="section-title">
          कैसे काम करता है?
          <span className="section-title-en">How It Works</span>
        </h2>
        
        <div className="steps-grid">
          <div className="step-card">
            <div className="step-number">1</div>
            <div className="step-icon">
              <Phone size={40} />
            </div>
            <h3 className="step-title">आवाज भेजें</h3>
            <p className="step-description">
              WhatsApp पर आवाज में बोलें:
              <br />
              <em>"राम को 2 चावल बेचा"</em>
              <br />
              या
              <br />
              <em>"sold 2 rice to ram"</em>
            </p>
          </div>

          <div className="step-card">
            <div className="step-number">2</div>
            <div className="step-icon">
              <Receipt size={40} />
            </div>
            <h3 className="step-title">बिल बनेगा</h3>
            <p className="step-description">
              अपने आप बिल बन जाएगा
              <br />
              ग्राहक का नाम, सामान, दाम
              <br />
              सब लिख जाएगा
            </p>
          </div>

          <div className="step-card">
            <div className="step-number">3</div>
            <div className="step-icon">
              <Mail size={40} />
            </div>
            <h3 className="step-title">ईमेल मिलेगा</h3>
            <p className="step-description">
              ग्राहक को बिल की PDF
              <br />
              ईमेल से भेज दी जाएगी
              <br />
              पेमेंट लिंक भी रहेगा
            </p>
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
      <div className="help-section">
        <div className="help-card">
          <HelpCircle size={48} />
          <h3>मदद चाहिए?</h3>
          <p className="help-text">
            WhatsApp पर आवाज भेजने के लिए:
            <br />
            <strong>+1 415 523 8886</strong>
            <br />
            <br />
            पहले "join" लिखकर भेजें
            <br />
            फिर आवाज भेजें
          </p>
        </div>
      </div>
    </div>
  );
};

export default Home;
