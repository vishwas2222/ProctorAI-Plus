import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

// Import our new pages
import LoginPage from './pages/LoginPage';
import StudentDashboard from './pages/StudentDashboard';
import AdminDashboard from './pages/AdminDashboard';
import ExamPage from './pages/ExamPage';

function App() {
  return (
    <Routes>
      {/* By default, navigate to the login page */}
      <Route path="/" element={<Navigate to="/login" />} />

      <Route path="/login" element={<LoginPage />} />
      <Route path="/admin/dashboard" element={<AdminDashboard />} />
      <Route path="/student/dashboard" element={<StudentDashboard />} />
      <Route path="/exam/:examId" element={<ExamPage />} />

      {/* A catch-all route for non-existent pages */}
      <Route path="*" element={<h1>404: Page Not Found</h1>} />
    </Routes>
  );
}

export default App;