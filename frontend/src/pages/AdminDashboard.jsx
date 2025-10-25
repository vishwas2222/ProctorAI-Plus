import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Header from '../components/Header';

const API_URL = 'http://127.0.0.1:5000';

function AdminDashboard() {
  const [user, setUser] = useState(null);
  // ✨ MODIFIED: Default to 'view_exams'
  const [view, setView] = useState('view_exams');
  
  // For 'View Exams'
  const [exams, setExams] = useState([]);
  const [loadingExams, setLoadingExams] = useState(false);

  // For 'Create Exam'
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [loadingCreate, setLoadingCreate] = useState(false);

  // ✨ NEW: For 'Assign Exam'
  const [students, setStudents] = useState([]);
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [assignExamId, setAssignExamId] = useState('');
  const [assignStudentId, setAssignStudentId] = useState('');
  const [loadingAssign, setLoadingAssign] = useState(false);

  // General messages
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const storedUser = JSON.parse(localStorage.getItem('proctorUser'));
    if (storedUser) {
      setUser(storedUser);
    }
    // Fetch exams on initial load
    fetchExams();
  }, []);

  // Fetch data depending on the view
  useEffect(() => {
    if (view === 'view_exams') {
      fetchExams();
    } else if (view === 'assign_exam') {
      // Fetch both exams and students
      if (exams.length === 0) fetchExams();
      fetchStudents();
    }
  }, [view]); // Re-run when view changes

  const fetchExams = async () => {
    setLoadingExams(true);
    setError('');
    try {
      const response = await axios.get(`${API_URL}/api/exams`);
      setExams(response.data);
      // If we're loading exams for the assign tab, set the default selection
      if (response.data.length > 0) {
        setAssignExamId(response.data[0].id);
      }
    } catch (err) {
      setError('Failed to fetch exams.');
    } finally {
      setLoadingExams(false);
    }
  };

  // ✨ NEW: Function to fetch students
  const fetchStudents = async () => {
    setLoadingStudents(true);
    setError('');
    try {
      const response = await axios.get(`${API_URL}/api/students`);
      setStudents(response.data);
      if (response.data.length > 0) {
        setAssignStudentId(response.data[0].id);
      }
    } catch (err) {
      setError('Failed to fetch students.');
    } finally {
      setLoadingStudents(false);
    }
  };

  const handleCreateExam = async (e) => {
    e.preventDefault();
    if (!user) {
      setError('You must be logged in to create an exam.');
      return;
    }
    setLoadingCreate(true);
    setError('');
    setSuccess('');
    try {
      const payload = { title, description, admin_id: user.id };
      await axios.post(`${API_URL}/api/exams`, payload);
      setSuccess('Exam created successfully!');
      setTitle('');
      setDescription('');
      setView('view_exams'); // Switch back to view exams
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to create exam.');
    } finally {
      setLoadingCreate(false);
    }
  };

  // ✨ NEW: Function to assign an exam
  const handleAssignExam = async (e) => {
    e.preventDefault();
    if (!assignExamId || !assignStudentId) {
      setError('Please select both an exam and a student.');
      return;
    }
    setLoadingAssign(true);
    setError('');
    setSuccess('');
    try {
      const payload = { exam_id: assignExamId, student_id: assignStudentId };
      await axios.post(`${API_URL}/api/assign`, payload);
      setSuccess('Exam assigned successfully!');
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to assign exam.');
    } finally {
      setLoadingAssign(false);
    }
  };

  // Helper function to switch views and clear messages
  const changeView = (newView) => {
    setView(newView);
    setError('');
    setSuccess('');
  };

  if (!user) {
    return <div className="min-h-screen bg-gray-100 flex items-center justify-center">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Header username={user.username} portalType="Admin" />
      
      <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        {/* Navigation Tabs */}
        <div className="mb-6">
          <nav className="flex space-x-4" aria-label="Tabs">
            <button
              onClick={() => changeView('view_exams')}
              className={`px-4 py-2 font-medium rounded-md text-sm ${view === 'view_exams' ? 'bg-indigo-600 text-white shadow-sm' : 'text-gray-600 bg-white hover:bg-gray-50'}`}
            >
              View Exams
            </button>
            <button
              onClick={() => changeView('create_exam')}
              className={`px-4 py-2 font-medium rounded-md text-sm ${view === 'create_exam' ? 'bg-indigo-600 text-white shadow-sm' : 'text-gray-600 bg-white hover:bg-gray-50'}`}
            >
              Create New Exam
            </button>
            {/* ✨ NEW: Assign Exam Tab */}
            <button
              onClick={() => changeView('assign_exam')}
              className={`px-4 py-2 font-medium rounded-md text-sm ${view === 'assign_exam' ? 'bg-indigo-600 text-white shadow-sm' : 'text-gray-600 bg-white hover:bg-gray-50'}`}
            >
              Assign Exam
            </button>
          </nav>
        </div>

        {/* Success/Error Messages */}
        {error && <div className="mb-4 p-3 bg-red-100 text-red-700 border border-red-200 rounded-md">{error}</div>}
        {success && <div className="mb-4 p-3 bg-green-100 text-green-700 border border-green-200 rounded-md">{success}</div>}

        {/* View Exams Content */}
        {view === 'view_exams' && (
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">All Exams</h2>
            {loadingExams ? <p>Loading exams...</p> : (
              <div className="space-y-4">
                {exams.length === 0 ? <p>No exams created yet.</p> : exams.map((exam) => (
                  <div key={exam.id} className="p-4 border border-gray-200 rounded-lg flex justify-between items-center transition-shadow hover:shadow-lg">
                    <div>
                      <h3 className="text-lg font-semibold text-indigo-700">{exam.title}</h3>
                      <p className="text-sm text-gray-600">{exam.description || 'No description'}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        Created by: {exam.admin_username} on {new Date(exam.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <button className="px-3 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
                      View Sessions
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Create Exam Content */}
        {view === 'create_exam' && (
          <div className="bg-white p-6 rounded-lg shadow-md max-w-2xl mx-auto">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">Create a New Exam</h2>
            {/* ... (form is unchanged from last step) ... */}
            <form onSubmit={handleCreateExam} className="space-y-4">
              <div>
                <label htmlFor="title" className="block text-sm font-medium text-gray-700">Exam Title</label>
                <input type="text" id="title" value={title} onChange={(e) => setTitle(e.target.value)} required className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
              </div>
              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700">Description (Optional)</label>
                <textarea id="description" rows="3" value={description} onChange={(e) => setDescription(e.target.value)} className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" />
              </div>
              <div>
                <button type="submit" disabled={loadingCreate} className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-indigo-400">
                  {loadingCreate ? 'Creating...' : 'Create Exam'}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* ✨ NEW: Assign Exam Content */}
        {view === 'assign_exam' && (
          <div className="bg-white p-6 rounded-lg shadow-md max-w-2xl mx-auto">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">Assign Exam to Student</h2>
            <form onSubmit={handleAssignExam} className="space-y-4">
              <div>
                <label htmlFor="exam" className="block text-sm font-medium text-gray-700">
                  Select Exam
                </label>
                <select
                  id="exam"
                  value={assignExamId}
                  onChange={(e) => setAssignExamId(e.target.value)}
                  disabled={loadingExams}
                  className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                >
                  {exams.map((exam) => (
                    <option key={exam.id} value={exam.id}>{exam.title}</option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="student" className="block text-sm font-medium text-gray-700">
                  Select Student
                </label>
                <select
                  id="student"
                  value={assignStudentId}
                  onChange={(e) => setAssignStudentId(e.target.value)}
                  disabled={loadingStudents}
                  className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                >
                  {students.map((student) => (
                    <option key={student.id} value={student.id}>{student.username}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <button
                  type="submit"
                  disabled={loadingAssign}
                  className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-indigo-400"
                >
                  {loadingAssign ? 'Assigning...' : 'Assign Exam'}
                </button>
              </div>
            </form>
          </div>
        )}

      </div>
    </div>
  );
}

export default AdminDashboard;