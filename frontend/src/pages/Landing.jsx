import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { ArrowRight, CheckCircle, Zap, Shield, BarChart3, Mail, Phone, Menu, X, Play, Activity, FileText, Users, Clock } from 'lucide-react';

export default function Landing() {
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [demoForm, setDemoForm] = useState({ name: '', email: '', company: '', message: '' });
  const [contactForm, setContactForm] = useState({ name: '', email: '', subject: '', message: '' });
  const [blogPosts, setBlogPosts] = useState([]);
  const [demoSubmitting, setDemoSubmitting] = useState(false);
  const [contactSubmitting, setContactSubmitting] = useState(false);

  useEffect(() => {
    fetchBlogPosts();
  }, []);

  const fetchBlogPosts = async () => {
    try {
      const res = await api.getBlogPosts(null, 3, 0);
      setBlogPosts(res.data.data || []);
    } catch (err) {
      console.error('Failed to fetch blog posts:', err);
    }
  };

  const handleDemoSubmit = async (e) => {
    e.preventDefault();
    setDemoSubmitting(true);
    try {
      await api.submitDemoRequest(demoForm);
      alert('Demo request submitted! We will contact you soon.');
      setDemoForm({ name: '', email: '', company: '', message: '' });
    } catch (err) {
      console.error('Failed to submit demo request:', err);
      alert('Failed to submit demo request. Please try again.');
    } finally {
      setDemoSubmitting(false);
    }
  };

  const handleContactSubmit = async (e) => {
    e.preventDefault();
    setContactSubmitting(true);
    try {
      await api.submitContactForm(contactForm);
      alert('Message sent! We will get back to you soon.');
      setContactForm({ name: '', email: '', subject: '', message: '' });
    } catch (err) {
      console.error('Failed to send message:', err);
      alert('Failed to send message. Please try again.');
    } finally {
      setContactSubmitting(false);
    }
  };

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif', backgroundColor: '#ffffff' }}>
      {/* Navigation */}
      <nav style={{ 
        position: 'fixed', 
        top: 0, 
        left: 0, 
        right: 0, 
        background: '#ffffff',
        borderBottom: '1px solid #e5e7eb',
        zIndex: 1000,
        padding: '16px 24px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)'
      }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ 
              width: '40px', 
              height: '40px', 
              borderRadius: '8px', 
              background: '#0284c7',
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              fontWeight: 700,
              color: 'white',
              fontSize: '1.25rem'
            }}>
              M
            </div>
            <span style={{ fontSize: '1.25rem', fontWeight: 700, color: '#1e293b' }}>MedClaim</span>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
              <a href="#features" style={{ color: '#64748b', textDecoration: 'none', fontSize: '0.875rem', fontWeight: 500 }}>Features</a>
              <a href="#how-it-works" style={{ color: '#64748b', textDecoration: 'none', fontSize: '0.875rem', fontWeight: 500 }}>How It Works</a>
              <a href="#docs" style={{ color: '#64748b', textDecoration: 'none', fontSize: '0.875rem', fontWeight: 500 }}>Docs</a>
              <a href="#blog" style={{ color: '#64748b', textDecoration: 'none', fontSize: '0.875rem', fontWeight: 500 }}>Blog</a>
              <a href="#contact" style={{ color: '#64748b', textDecoration: 'none', fontSize: '0.875rem', fontWeight: 500 }}>Contact</a>
            </div>
            <button
              onClick={() => navigate('/login')}
              style={{
                padding: '10px 24px',
                borderRadius: '6px',
                background: '#0284c7',
                color: 'white',
                border: 'none',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: '0.875rem',
                boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
              }}
            >
              Login
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section style={{ 
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(180deg, #f0f9ff 0%, #ffffff 100%)',
        padding: '120px 24px 60px'
      }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', textAlign: 'center' }}>
          <div style={{ 
            display: 'inline-block',
            padding: '8px 16px',
            borderRadius: '20px',
            background: '#e0f2fe',
            color: '#0284c7',
            fontSize: '0.875rem',
            fontWeight: 600,
            marginBottom: '24px'
          }}>
            AI-Powered Medical Claims Processing
          </div>
          
          <h1 style={{ 
            fontSize: 'clamp(2.5rem, 5vw, 4rem)',
            fontWeight: 800,
            color: '#0f172a',
            lineHeight: 1.2,
            marginBottom: '24px'
          }}>
            Automate Medical Claims<br />with AI Intelligence
          </h1>
          
          <p style={{ 
            fontSize: '1.125rem',
            color: '#64748b',
            maxWidth: '600px',
            margin: '0 auto 40px',
            lineHeight: 1.7
          }}>
            Reduce claim denials by 40% with our AI-powered audit system. 
            Real-time code validation, denial prediction, and collaborative approval workflows.
          </p>
          
          <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', flexWrap: 'wrap' }}>
            <button
              onClick={() => document.getElementById('demo').scrollIntoView({ behavior: 'smooth' })}
              style={{
                padding: '16px 32px',
                borderRadius: '8px',
                background: '#0284c7',
                color: 'white',
                border: 'none',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: '1rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: '0 4px 6px rgba(2, 132, 199, 0.2)'
              }}
            >
              Request Demo <ArrowRight size={20} />
            </button>
            <button
              onClick={() => document.getElementById('how-it-works').scrollIntoView({ behavior: 'smooth' })}
              style={{
                padding: '16px 32px',
                borderRadius: '8px',
                background: 'white',
                color: '#0f172a',
                border: '2px solid #e5e7eb',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: '1rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <Play size={20} /> See How It Works
            </button>
          </div>
          
          <div style={{ marginTop: '48px', display: 'flex', gap: '48px', justifyContent: 'center', flexWrap: 'wrap' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2.5rem', fontWeight: 800, color: '#0284c7' }}>40%</div>
              <div style={{ fontSize: '0.875rem', color: '#64748b', fontWeight: 500 }}>Fewer Denials</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2.5rem', fontWeight: 800, color: '#0284c7' }}>95%</div>
              <div style={{ fontSize: '0.875rem', color: '#64748b', fontWeight: 500 }}>Accuracy Rate</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '2.5rem', fontWeight: 800, color: '#0284c7' }}>10x</div>
              <div style={{ fontSize: '0.875rem', color: '#64748b', fontWeight: 500 }}>Faster Processing</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" style={{ padding: '100px 24px', background: '#ffffff' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '64px' }}>
            <h2 style={{ fontSize: '2.5rem', fontWeight: 700, color: '#0f172a', marginBottom: '16px' }}>
              Powerful Features
            </h2>
            <p style={{ fontSize: '1.125rem', color: '#64748b' }}>
              Everything you need to streamline your claims processing
            </p>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '32px' }}>
            {[
              {
                icon: <Activity size={32} color="#0284c7" />,
                title: 'AI-Powered Code Audit',
                description: 'Automatically detect coding errors before submission with 95% accuracy using advanced AI models.'
              },
              {
                icon: <Shield size={32} color="#059669" />,
                title: 'Denial Prediction',
                description: 'Predict claim denials before they happen with risk scoring and actionable insights.'
              },
              {
                icon: <CheckCircle size={32} color="#10b981" />,
                title: 'Approval Workflows',
                description: 'Configurable multi-step approval chains with timeout escalation and role-based access.'
              },
              {
                icon: <BarChart3 size={32} color="#d97706" />,
                title: 'Real-time Analytics',
                description: 'Track denial rates, payer performance, and team productivity with comprehensive dashboards.'
              },
              {
                icon: <Mail size={32} color="#dc2626" />,
                title: 'Collaborative Comments',
                description: 'Threaded comments on claims for team collaboration and audit trail documentation.'
              },
              {
                icon: <Play size={32} color="#0891b2" />,
                title: 'Voice AI Assistant',
                description: 'Natural language interface to query claims and get instant answers using voice commands.'
              }
            ].map((feature, index) => (
              <div key={index} style={{
                padding: '32px',
                borderRadius: '12px',
                background: '#ffffff',
                border: '1px solid #e5e7eb',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
                transition: 'box-shadow 0.3s ease'
              }}>
                <div style={{ marginBottom: '16px' }}>{feature.icon}</div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#0f172a', marginBottom: '12px' }}>
                  {feature.title}
                </h3>
                <p style={{ fontSize: '0.875rem', color: '#64748b', lineHeight: 1.6 }}>
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" style={{ padding: '100px 24px', background: '#f8fafc' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '64px' }}>
            <h2 style={{ fontSize: '2.5rem', fontWeight: 700, color: '#0f172a', marginBottom: '16px' }}>
              How It Works
            </h2>
            <p style={{ fontSize: '1.125rem', color: '#64748b' }}>
              Simple 3-step process to transform your claims workflow
            </p>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '48px' }}>
            {[
              {
                step: '01',
                title: 'Upload Claims',
                description: 'Upload medical claims in any format. Our system automatically extracts and validates the data.'
              },
              {
                step: '02',
                title: 'AI Analysis',
                description: 'Our AI audits codes, predicts denials, and flags issues for human review when needed.'
              },
              {
                step: '03',
                title: 'Approve & Submit',
                description: 'Review flagged claims, collaborate with your team, and submit clean claims to payers.'
              }
            ].map((item, index) => (
              <div key={index} style={{ textAlign: 'center' }}>
                <div style={{ 
                  width: '80px',
                  height: '80px',
                  borderRadius: '50%',
                  background: '#0284c7',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.5rem',
                  fontWeight: 800,
                  color: 'white',
                  margin: '0 auto 24px',
                  boxShadow: '0 4px 6px rgba(2, 132, 199, 0.2)'
                }}>
                  {item.step}
                </div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#0f172a', marginBottom: '12px' }}>
                  {item.title}
                </h3>
                <p style={{ fontSize: '0.875rem', color: '#64748b', lineHeight: 1.6 }}>
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Demo Request */}
      <section id="demo" style={{ padding: '100px 24px', background: '#ffffff' }}>
        <div style={{ maxWidth: '600px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '48px' }}>
            <h2 style={{ fontSize: '2.5rem', fontWeight: 700, color: '#0f172a', marginBottom: '16px' }}>
              Request a Demo
            </h2>
            <p style={{ fontSize: '1.125rem', color: '#64748b' }}>
              See MedClaim in action with a personalized demo
            </p>
          </div>
          
          <form onSubmit={handleDemoSubmit} style={{ 
            padding: '40px',
            borderRadius: '12px',
            background: '#ffffff',
            border: '1px solid #e5e7eb',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px'
          }}>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.875rem', color: '#374151', fontWeight: 600 }}>
                Full Name
              </label>
              <input
                type="text"
                value={demoForm.name}
                onChange={(e) => setDemoForm({ ...demoForm, name: e.target.value })}
                required
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  borderRadius: '6px',
                  border: '1px solid #d1d5db',
                  background: '#ffffff',
                  color: '#1f2937',
                  fontSize: '1rem',
                  boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.875rem', color: '#374151', fontWeight: 600 }}>
                Email
              </label>
              <input
                type="email"
                value={demoForm.email}
                onChange={(e) => setDemoForm({ ...demoForm, email: e.target.value })}
                required
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  borderRadius: '6px',
                  border: '1px solid #d1d5db',
                  background: '#ffffff',
                  color: '#1f2937',
                  fontSize: '1rem',
                  boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.875rem', color: '#374151', fontWeight: 600 }}>
                Company
              </label>
              <input
                type="text"
                value={demoForm.company}
                onChange={(e) => setDemoForm({ ...demoForm, company: e.target.value })}
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  borderRadius: '6px',
                  border: '1px solid #d1d5db',
                  background: '#ffffff',
                  color: '#1f2937',
                  fontSize: '1rem',
                  boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.875rem', color: '#374151', fontWeight: 600 }}>
                Message (Optional)
              </label>
              <textarea
                value={demoForm.message}
                onChange={(e) => setDemoForm({ ...demoForm, message: e.target.value })}
                rows={4}
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  borderRadius: '6px',
                  border: '1px solid #d1d5db',
                  background: '#ffffff',
                  color: '#1f2937',
                  fontSize: '1rem',
                  resize: 'vertical',
                  boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
                }}
              />
            </div>
            <button
              type="submit"
              disabled={demoSubmitting}
              style={{
                padding: '16px 32px',
                borderRadius: '6px',
                background: '#0284c7',
                color: 'white',
                border: 'none',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: '1rem',
                opacity: demoSubmitting ? 0.6 : 1,
                boxShadow: '0 4px 6px rgba(2, 132, 199, 0.2)'
              }}
            >
              {demoSubmitting ? 'Submitting...' : 'Request Demo'}
            </button>
          </form>
        </div>
      </section>

      {/* Blog Section */}
      <section id="blog" style={{ padding: '100px 24px', background: '#f8fafc' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '64px' }}>
            <h2 style={{ fontSize: '2.5rem', fontWeight: 700, color: '#0f172a', marginBottom: '16px' }}>
              Latest Insights
            </h2>
            <p style={{ fontSize: '1.125rem', color: '#64748b' }}>
              Stay updated with industry trends and best practices
            </p>
          </div>
          
          {blogPosts.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '32px' }}>
              {blogPosts.map((post) => (
                <div key={post.id} style={{
                  padding: '24px',
                  borderRadius: '12px',
                  background: '#ffffff',
                  border: '1px solid #e5e7eb',
                  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
                  cursor: 'pointer',
                  transition: 'box-shadow 0.3s ease'
                }}>
                  <div style={{ fontSize: '0.75rem', color: '#0284c7', marginBottom: '12px', fontWeight: 600 }}>
                    {post.category || 'General'}
                  </div>
                  <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#0f172a', marginBottom: '12px' }}>
                    {post.title}
                  </h3>
                  <p style={{ fontSize: '0.875rem', color: '#64748b', lineHeight: 1.6, marginBottom: '16px' }}>
                    {post.excerpt || post.content?.substring(0, 150) + '...'}
                  </p>
                  <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
                    {new Date(post.published_at || post.created_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '48px', color: '#9ca3af' }}>
              No blog posts available yet.
            </div>
          )}
        </div>
      </section>

      {/* Documentation Section */}
      <section id="docs" style={{ padding: '100px 24px', background: '#ffffff' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '64px' }}>
            <h2 style={{ fontSize: '2.5rem', fontWeight: 700, color: '#0f172a', marginBottom: '16px' }}>
              Developer Documentation
            </h2>
            <p style={{ fontSize: '1.125rem', color: '#64748b' }}>
              Integrate MedClaim into your workflow with our comprehensive API
            </p>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '32px' }}>
            {[
              {
                title: 'Authentication',
                description: 'Secure JWT-based authentication with Supabase Auth integration.',
                endpoints: [
                  'POST /auth/login',
                  'POST /auth/logout',
                  'GET /auth/me',
                  'POST /auth/refresh'
                ]
              },
              {
                title: 'Claims API',
                description: 'Manage medical claims with AI-powered audit and denial prediction.',
                endpoints: [
                  'GET /claims',
                  'GET /claims/{id}',
                  'POST /claims',
                  'POST /claims/{id}/approve',
                  'POST /claims/{id}/reject'
                ]
              },
              {
                title: 'Workflows API',
                description: 'Configure approval workflows and manage claim approvals.',
                endpoints: [
                  'GET /workflows',
                  'POST /workflows',
                  'GET /workflows/{id}',
                  'POST /workflows/{id}/steps',
                  'POST /workflows/claims/{id}/initiate'
                ]
              },
              {
                title: 'Comments API',
                description: 'Add threaded comments to claims for team collaboration.',
                endpoints: [
                  'GET /comments/claims/{claim_id}',
                  'POST /comments',
                  'PUT /comments/{id}',
                  'DELETE /comments/{id}'
                ]
              },
              {
                title: 'Analytics API',
                description: 'Get denial analytics and performance metrics.',
                endpoints: [
                  'GET /analytics/denials',
                  'GET /analytics/performance',
                  'GET /analytics/trends'
                ]
              },
              {
                title: 'Public API',
                description: 'Public endpoints for demo requests and blog content.',
                endpoints: [
                  'POST /public/lead/demo',
                  'POST /public/lead/contact',
                  'GET /public/blog',
                  'GET /public/blog/{id}'
                ]
              }
            ].map((section, index) => (
              <div key={index} style={{
                padding: '32px',
                borderRadius: '12px',
                background: '#ffffff',
                border: '1px solid #e5e7eb',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)'
              }}>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#0f172a', marginBottom: '12px' }}>
                  {section.title}
                </h3>
                <p style={{ fontSize: '0.875rem', color: '#64748b', lineHeight: 1.6, marginBottom: '16px' }}>
                  {section.description}
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {section.endpoints.map((endpoint, i) => (
                    <div key={i} style={{
                      padding: '8px 12px',
                      borderRadius: '6px',
                      background: '#f0f9ff',
                      fontFamily: 'monospace',
                      fontSize: '0.75rem',
                      color: '#0284c7',
                      border: '1px solid #e0f2fe'
                    }}>
                      {endpoint}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
          
          <div style={{ marginTop: '48px', textAlign: 'center' }}>
            <a
              href="/api-docs"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '16px 32px',
                borderRadius: '6px',
                background: '#0284c7',
                color: 'white',
                textDecoration: 'none',
                fontWeight: 600,
                fontSize: '1rem',
                boxShadow: '0 4px 6px rgba(2, 132, 199, 0.2)'
              }}
            >
              View Full API Documentation <ArrowRight size={20} />
            </a>
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section id="contact" style={{ padding: '100px 24px', background: '#f8fafc' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '64px' }}>
            <div>
              <h2 style={{ fontSize: '2.5rem', fontWeight: 700, color: '#0f172a', marginBottom: '16px' }}>
                Get in Touch
              </h2>
              <p style={{ fontSize: '1.125rem', color: '#64748b', marginBottom: '32px' }}>
                Have questions? We'd love to hear from you.
              </p>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div style={{ 
                    width: '48px',
                    height: '48px',
                    borderRadius: '12px',
                    background: '#e0f2fe',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <Mail size={24} color="#0284c7" />
                  </div>
                  <div>
                    <div style={{ fontSize: '0.875rem', color: '#64748b' }}>Email</div>
                    <div style={{ fontSize: '1rem', color: '#0f172a', fontWeight: 600 }}>contact@medclaim.ai</div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div style={{ 
                    width: '48px',
                    height: '48px',
                    borderRadius: '12px',
                    background: '#f0fdf4',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <Phone size={24} color="#059669" />
                  </div>
                  <div>
                    <div style={{ fontSize: '0.875rem', color: '#64748b' }}>Phone</div>
                    <div style={{ fontSize: '1rem', color: '#0f172a', fontWeight: 600 }}>+1 (555) 123-4567</div>
                  </div>
                </div>
              </div>
            </div>
            
            <form onSubmit={handleContactSubmit} style={{ 
              padding: '40px',
              borderRadius: '12px',
              background: '#ffffff',
              border: '1px solid #e5e7eb',
              boxShadow: '0 4px 6px rgba(0, 0, 0, 0.05)',
              display: 'flex',
              flexDirection: 'column',
              gap: '20px'
            }}>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.875rem', color: '#374151', fontWeight: 600 }}>
                  Name
                </label>
                <input
                  type="text"
                  value={contactForm.name}
                  onChange={(e) => setContactForm({ ...contactForm, name: e.target.value })}
                  required
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    borderRadius: '6px',
                    border: '1px solid #d1d5db',
                    background: '#ffffff',
                    color: '#1f2937',
                    fontSize: '1rem',
                    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.875rem', color: '#374151', fontWeight: 600 }}>
                  Email
                </label>
                <input
                  type="email"
                  value={contactForm.email}
                  onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })}
                  required
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    borderRadius: '6px',
                    border: '1px solid #d1d5db',
                    background: '#ffffff',
                    color: '#1f2937',
                    fontSize: '1rem',
                    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.875rem', color: '#374151', fontWeight: 600 }}>
                  Subject
                </label>
                <input
                  type="text"
                  value={contactForm.subject}
                  onChange={(e) => setContactForm({ ...contactForm, subject: e.target.value })}
                  required
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    borderRadius: '6px',
                    border: '1px solid #d1d5db',
                    background: '#ffffff',
                    color: '#1f2937',
                    fontSize: '1rem',
                    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.875rem', color: '#374151', fontWeight: 600 }}>
                  Message
                </label>
                <textarea
                  value={contactForm.message}
                  onChange={(e) => setContactForm({ ...contactForm, message: e.target.value })}
                  rows={4}
                  required
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    borderRadius: '6px',
                    border: '1px solid #d1d5db',
                    background: '#ffffff',
                    color: '#1f2937',
                    fontSize: '1rem',
                    resize: 'vertical',
                    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
                  }}
                />
              </div>
              <button
                type="submit"
                disabled={contactSubmitting}
                style={{
                  padding: '16px 32px',
                  borderRadius: '6px',
                  background: '#0284c7',
                  color: 'white',
                  border: 'none',
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontSize: '1rem',
                  opacity: contactSubmitting ? 0.6 : 1,
                  boxShadow: '0 4px 6px rgba(2, 132, 199, 0.2)'
                }}
              >
                {contactSubmitting ? 'Sending...' : 'Send Message'}
              </button>
            </form>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ padding: '48px 24px', background: '#ffffff', borderTop: '1px solid #e5e7eb' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', textAlign: 'center' }}>
          <div style={{ marginBottom: '24px' }}>
            <span style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0f172a' }}>MedClaim</span>
          </div>
          <p style={{ fontSize: '0.875rem', color: '#9ca3af' }}>
            © 2024 MedClaim. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
