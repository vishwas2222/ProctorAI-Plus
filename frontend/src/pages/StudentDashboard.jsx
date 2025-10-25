import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  BookMarked, BookOpenCheck, CalendarDays, PlayCircle,
  Loader2, AlertTriangle, Inbox, LogOut, Search,
  Filter, RefreshCw, Clock
} from 'lucide-react';

const API_URL = 'http://127.0.0.1:5000';

const ExamCard = ({ exam, onStart }) => {
  const scheduled = exam.scheduled_at || exam.start_time || exam.assigned_at;
  const scheduledDate = scheduled ? new Date(scheduled) : null;
  const isUpcoming = scheduledDate ? scheduledDate.getTime() > Date.now() : false;
  const status = exam.completed ? 'Completed' : isUpcoming ? 'Available' : 'Available';

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 flex flex-col sm:flex-row justify-between sm:items-center transition-all duration-300 transform hover:shadow-xl hover:-translate-y-1 animate-fade-in-up border-l-4 border-indigo-500 shadow-md hover:border-indigo-600">
      <div className="mb-4 sm:mb-0 flex-grow mr-4">
        <h3 className="text-lg lg:text-xl font-semibold text-indigo-700 flex items-center gap-2">
          <BookOpenCheck className="w-5 h-5 lg:w-6 lg:h-6 flex-shrink-0" />
          <span className="truncate">{exam.title || 'Untitled Exam'}</span>
          <span className={`ml-2 inline-flex items-center text-xs font-medium px-2 py-0.5 rounded ${
            exam.completed ? 'bg-green-100 text-green-700' : 
            'bg-indigo-100 text-indigo-700'
          }`}>
            {status}
          </span>
        </h3>
        <p className="text-sm text-gray-600 mt-2 line-clamp-2">
          {exam.description || 'No description provided.'}
        </p>
        <div className="mt-3 text-sm text-gray-500 flex flex-wrap gap-3 items-center">
          <span className="flex items-center gap-1.5">
            <CalendarDays className="w-4 h-4" />
            {scheduledDate ? scheduledDate.toLocaleString() : 'Not scheduled'}
          </span>
          {exam.duration && (
            <span className="flex items-center gap-1.5">
              <Clock className="w-4 h-4" />
              {exam.duration} mins
            </span>
          )}
        </div>
      </div>
      
      <div className="flex-shrink-0 mt-4 sm:mt-0 w-full sm:w-auto">
        <button
          onClick={() => onStart(exam.exam_id)}
          className="group w-full sm:w-auto flex items-center justify-center px-6 py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white text-base font-semibold rounded-lg shadow-md hover:shadow-lg hover:from-indigo-600 hover:to-purple-700 transition-all duration-300 transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          disabled={exam.completed && !exam.reviewable}
        >
          <PlayCircle className="w-5 h-5 mr-2 transition-transform duration-300 group-hover:translate-x-1" />
          {exam.completed ? 'View Results' : 'Start Exam'}
        </button>
      </div>
    </div>
  );
};

const DashboardHeader = ({ onLogout }) => (
  <nav className="bg-white/90 backdrop-blur-lg shadow-sm border-b border-gray-200/50 sticky top-0 z-50 w-full">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="flex justify-between items-center h-20">
        <div className="flex items-center gap-2">
          <span className="text-3xl font-bold flex items-center">
            <span className="mr-2 text-3xl">🛡️</span>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-800 to-indigo-900">
              ProctorAI+
            </span>
          </span>
          <span className="ml-2 text-sm font-medium bg-indigo-100 text-indigo-700 rounded-lg px-3 py-1 inline-block border border-indigo-200 shadow-sm hidden sm:inline-block">
            Student Portal
          </span>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={onLogout}
            className="group flex items-center px-4 py-2 rounded-lg text-base font-medium text-red-600 bg-gray-100 hover:bg-red-100 hover:text-red-700 transition-all duration-200 border border-gray-200 hover:border-red-300 self-center shadow-sm hover:shadow-md"
          >
            <LogOut className="w-5 h-5 mr-0 sm:mr-2 transition-all" />
            <span className="hidden sm:block">Logout</span>
          </button>
        </div>
      </div>
    </div>
  </nav>
);

function StudentDashboard() {
  const [user, setUser] = useState(null);
  const [assignedExams, setAssignedExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [refreshing, setRefreshing] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const storedUser = JSON.parse(localStorage.getItem('proctorUser'));
    if (!storedUser) {
      navigate('/login');
      return;
    }
    setUser(storedUser);
    fetchMyExams(storedUser.id);
  }, [navigate]);

  const fetchMyExams = async (studentId) => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.get(`${API_URL}/api/my_exams/${studentId}`);
      setAssignedExams(response.data || []);
    } catch (err) {
      setError('Failed to fetch your assigned exams. Please try again later.');
      console.error("Fetch Exams Error:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleStartExam = (examId) => navigate(`/exam/${examId}`);
  
  const handleLogout = () => {
    localStorage.removeItem('proctorUser');
    navigate('/login');
  };

  const handleRefresh = () => {
    if (!user) return;
    setRefreshing(true);
    fetchMyExams(user.id);
  };

  const filteredExams = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return assignedExams
      .filter(exam => {
        if (q) {
          const title = (exam.title || '').toLowerCase();
          const desc = (exam.description || '').toLowerCase();
          if (!title.includes(q) && !desc.includes(q)) return false;
        }
        if (filter === 'completed') return exam.completed;
        return true;
      })
      .sort((a, b) => {
        const aTime = new Date(a.scheduled_at || a.start_time || a.assigned_at).getTime();
        const bTime = new Date(b.scheduled_at || b.start_time || b.assigned_at).getTime();
        return (aTime || 0) - (bTime || 0);
      });
  }, [assignedExams, searchQuery, filter]);

  const stats = useMemo(() => ({
    total: assignedExams.length,
    completed: assignedExams.filter(e => e.completed).length
  }), [assignedExams]);

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-white via-slate-50 to-gray-100 flex items-center justify-center">
        <Loader2 className="w-12 h-12 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-white via-slate-50 to-gray-100 text-gray-900 font-sans">
      <DashboardHeader onLogout={handleLogout} />
      
      <main className="max-w-7xl mx-auto py-10 px-4 sm:px-6 lg:px-8 space-y-8">
        <section className="bg-white border border-gray-200/80 rounded-2xl shadow-lg p-6 sm:p-8 animate-fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
            <div className="flex items-start gap-4">
              <div className="rounded-lg bg-indigo-50 p-3">
                <BookMarked className="w-7 h-7 text-indigo-600" />
              </div>
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
                  Hello, <span className="text-indigo-700">{user.username}</span>
                </h1>
                <p className="mt-1 text-sm text-gray-600">
                  Manage your exams, start assessments, and track progress.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto">
              <div className="relative flex-1">
                <div className="flex items-center bg-gray-50 border border-gray-200 rounded-md px-3 py-2">
                  <Search className="w-4 h-4 text-gray-400" />
                  <input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search exams..."
                    className="ml-2 w-full bg-transparent outline-none text-sm"
                  />
                </div>
              </div>

              <div className="hidden sm:flex items-center gap-2">
                <button
                  onClick={() => setFilter(prev => prev === 'all' ? 'completed' : 'all')}
                  className="flex items-center gap-2 px-3 py-2 rounded-md border border-gray-200 bg-white text-sm shadow-sm hover:shadow-md transition"
                >
                  <Filter className="w-4 h-4 text-gray-600" />
                  <span className="capitalize">{filter}</span>
                </button>

                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="px-3 py-2 rounded-md border border-gray-200 bg-white text-sm shadow-sm hover:shadow-md transition flex items-center gap-2"
                >
                  <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                  Refresh
                </button>
              </div>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4">
              <p className="text-sm text-indigo-700 font-semibold">Total Assigned</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">{stats.total}</p>
            </div>
            <div className="bg-white border border-gray-100 rounded-lg p-4">
              <p className="text-sm text-gray-600 font-medium">Completed</p>
              <p className="mt-1 text-2xl font-bold text-indigo-700">{stats.completed}</p>
            </div>
          </div>
        </section>

        <section className="bg-white border border-gray-200/80 rounded-2xl shadow-lg p-6 sm:p-10 animate-fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6">
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 break-words leading-tight flex items-center gap-3 mb-4 sm:mb-0">
              <BookMarked className="w-7 h-7 text-indigo-600 flex-shrink-0" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-700 to-purple-700">
                My Assigned Exams
              </span>
            </h2>
            {!loading && filteredExams.length > 0 && (
              <span className="text-sm font-medium bg-gray-100 text-gray-600 rounded-full px-3 py-1 self-start sm:self-center">
                {filteredExams.length} Exam{filteredExams.length !== 1 ? 's' : ''} Found
              </span>
            )}
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-300 text-red-700 rounded-lg flex items-center animate-fade-in shadow-sm">
              <AlertTriangle className="w-5 h-5 mr-3 flex-shrink-0" />
              {error}
            </div>
          )}

          {loading ? (
            <div className="flex justify-center items-center py-16">
              <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
              <span className="ml-4 text-xl text-gray-600">Loading exams...</span>
            </div>
          ) : (
            <div className="space-y-6">
              {filteredExams.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 px-4 text-center border-2 border-dashed border-gray-300 rounded-lg animate-fade-in bg-gray-50/50">
                  <Inbox className="w-16 h-16 text-gray-400 mb-4" />
                  <h3 className="text-2xl font-semibold text-gray-700">No Exams Found</h3>
                  <p className="mt-2 text-base text-gray-600">
                    {searchQuery 
                      ? 'No exams match your search criteria.' 
                      : 'You have no exams matching the selected filter.'}
                  </p>
                </div>
              ) : (
                filteredExams.map((exam, index) => (
                  <ExamCard
                    key={exam.exam_id || index}
                    exam={exam}
                    onStart={handleStartExam}
                  />
                ))
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default StudentDashboard;
