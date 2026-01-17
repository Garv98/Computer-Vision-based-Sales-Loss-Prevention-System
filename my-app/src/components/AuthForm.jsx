import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import axios from 'axios';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';

// Validation Schemas
const loginSchema = yup.object({
  email: yup.string().required('Email is required').email('Invalid email format'),
  password: yup.string().required('Password is required'),
});

const signupSchema = yup.object({
  fullName: yup.string().required('Full Name is required'),
  email: yup.string().required('Email is required').email('Invalid email format'),
  password: yup.string()
    .required('Password is required')
    .min(8, 'Password must be at least 8 characters')
    .matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/, 
      'Password must contain uppercase, lowercase, number, and special character'),
  phone: yup.string().required('Phone Number is required').matches(/^\d{10}$/, 'Must be a valid 10-digit number'),
  shopName: yup.string().required('Shop Name is required'),
  shopAddress: yup.string().required('Shop Address is required'),
  role: yup.string().oneOf(['admin', 'staff'], 'Invalid role').required('Role is required'),
});

const AuthForm = ({ setIsAuthenticated }) => {
  const [activeTab, setActiveTab] = useState('login');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  
  useEffect(() => {
    document.documentElement.classList.remove('dark');
  }, []);

  const loginForm = useForm({
    resolver: yupResolver(loginSchema),
    mode: 'onChange',
  });

  const signupForm = useForm({
    resolver: yupResolver(signupSchema),
    mode: 'onChange',
  });

  const handleLogin = async (data) => {
    setIsLoading(true);
    try {
      const response = await axios.post('http://localhost:5000/api/auth/login', data);
      toast.success('Login successful! Welcome to VisionGuard.');
      
      // Store user info in localStorage
      localStorage.setItem('user', JSON.stringify(response.data.user));
      localStorage.setItem('isAuthenticated', 'true');
      
      // Mark as authenticated and redirect
      setIsAuthenticated(true);
      navigate('/dashboard');

    } catch (error) {
      toast.error(error.response?.data?.message || 'Invalid credentials');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignup = async (data) => {
    setIsLoading(true);
    try {
      const response = await axios.post('http://localhost:5000/api/auth/signup', data);
      toast.success(response.data.message || 'Signup successful! Please log in.');
      setActiveTab('login');
      signupForm.reset();
    } catch (error) {
      toast.error(error.response?.data?.message || 'Signup failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const renderInput = (name, placeholder, type = 'text', form) => (
    <input
      {...form.register(name)}
      type={type}
      placeholder={placeholder}
      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition duration-200"
    />
  );

  const renderError = (name, form) => {
    const error = form.formState.errors[name];
    return error ? <p className="text-red-500 text-sm mt-1">{error.message}</p> : null;
  };

  return (
    <div className="w-full max-w-lg">
      <div className="bg-white/95 backdrop-blur-sm rounded-2xl shadow-2xl p-8 border border-white/20">
        <div className="text-center mb-8">
          <div className="mx-auto w-24 h-24 bg-primary-600 rounded-full flex items-center justify-center mb-6 shadow-lg">
            <svg className="w-14 h-14 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          </div>
          <h1 className="text-4xl font-bold text-gray-800 mb-2">VisionGuard</h1>
          <p className="text-lg text-gray-700">Sales Loss Prevention for Your Shop</p>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 mb-6">
          <button
            onClick={() => setActiveTab('login')}
            className={`flex-1 py-3 px-6 font-semibold rounded-t-lg transition duration-200 ${
              activeTab === 'login'
                ? 'border-b-2 border-primary-600 text-primary-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Login
          </button>
          <button
            onClick={() => setActiveTab('signup')}
            className={`flex-1 py-3 px-6 font-semibold rounded-t-lg transition duration-200 ${
              activeTab === 'signup'
                ? 'border-b-2 border-primary-600 text-primary-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Sign Up
          </button>
        </div>

        {/* Form */}
        {activeTab === 'login' ? (
          <form onSubmit={loginForm.handleSubmit(handleLogin)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
              {renderInput('email', 'Enter your email', 'email', loginForm)}
              {renderError('email', loginForm)}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
              {renderInput('password', 'Enter your password', 'password', loginForm)}
              {renderError('password', loginForm)}
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-primary-600 text-white py-3 rounded-lg font-semibold hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 transition duration-200 disabled:opacity-50"
            >
              {isLoading ? 'Logging in...' : 'Log In'}
            </button>
          </form>
        ) : (
          <form onSubmit={signupForm.handleSubmit(handleSignup)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
              {renderInput('fullName', 'Enter your full name', 'text', signupForm)}
              {renderError('fullName', signupForm)}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
              {renderInput('email', 'Enter your email', 'email', signupForm)}
              {renderError('email', signupForm)}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
              {renderInput('password', 'Create a strong password', 'password', signupForm)}
              {renderError('password', signupForm)}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Phone Number</label>
              {renderInput('phone', 'Enter 10-digit phone number', 'tel', signupForm)}
              {renderError('phone', signupForm)}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Shop Name</label>
              {renderInput('shopName', 'Enter your shop name', 'text', signupForm)}
              {renderError('shopName', signupForm)}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Shop Address</label>
              {renderInput('shopAddress', 'Enter your shop address', 'text', signupForm)}
              {renderError('shopAddress', signupForm)}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Role</label>
              <select
                {...signupForm.register('role')}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition duration-200"
              >
                <option value="">Select Role</option>
                <option value="admin">Admin (Full Access)</option>
                <option value="staff">Staff (Limited Access)</option>
              </select>
              {renderError('role', signupForm)}
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-primary-600 text-white py-3 rounded-lg font-semibold hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 transition duration-200 disabled:opacity-50"
            >
              {isLoading ? 'Signing up...' : 'Sign Up'}
            </button>
          </form>
        )}

        {/* Switch Tab Link */}
        <p className="text-center text-sm text-gray-600 mt-6">
          {activeTab === 'login' ? "Don't have an account?" : "Already registered?"}
          <button
            onClick={() => setActiveTab(activeTab === 'login' ? 'signup' : 'login')}
            className="text-primary-600 font-semibold ml-1 hover:underline"
          >
            {activeTab === 'login' ? 'Sign Up' : 'Log In'}
          </button>
        </p>
      </div>
    </div>
  );
};

export default AuthForm;