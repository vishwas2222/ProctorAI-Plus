import React, { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import {
  BookOpen,
  Users,
  PlusCircle,
  LogOut,
  BookOpenCheck,
  AlertTriangle,
  CheckCircle,
  Loader2,
  Calendar,
  Clock,
  Trash2,
} from "lucide-react";

const API_URL = "https://proctorai-plus-1.onrender.com";

// 🌟 Admin Header
const AdminHeader = ({ onLogout }) => (
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
            Admin Portal
          </span>
        </div>
        <button
          onClick={onLogout}
          className="group flex items-center px-4 py-2 rounded-lg text-base font-medium text-red-600 bg-gray-100 hover:bg-red-100 hover:text-red-700 transition-all duration-200 border border-gray-200 hover:border-red-300 shadow-sm hover:shadow-md"
        >
          <LogOut className="w-5 h-5 mr-0 sm:mr-2 transition-all" />
          <span className="hidden sm:block">Logout</span>
        </button>
      </div>
    </div>
  </nav>
);

// 🌈 Navigation Tabs
const NavTab = ({ icon: Icon, label, isActive, onClick }) => (
  <button
    onClick={onClick}
    className={`flex items-center px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
      isActive
        ? "bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-md"
        : "bg-white text-gray-600 hover:bg-gray-50 border border-gray-200"
    }`}
  >
    <Icon
      className={`w-4 h-4 mr-2 ${isActive ? "text-white" : "text-gray-500"}`}
    />
    {label}
  </button>
);

function AdminDashboard() {
  const navigate = useNavigate();
  const [view, setView] = useState("view_exams");
  const [exams, setExams] = useState([]);
  const [students, setStudents] = useState([]);
  const [newExam, setNewExam] = useState({
    title: "",
    description: "",
    duration: "",
  });
  const [assignData, setAssignData] = useState({
    studentId: "",
    examId: "",
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    if (!localStorage.getItem("proctorUser")) {
      navigate("/login");
      return;
    }
    fetchDashboardData();
  }, []);

  // 📦 Fetch Data
  const fetchDashboardData = async () => {
    setLoading(true);
    setError("");
    try {
      const [examRes, studentRes] = await Promise.all([
        axios.get(`${API_URL}/api/exams`),
        axios.get(`${API_URL}/api/students`),
      ]);
      setExams(examRes.data || []);
      setStudents(studentRes.data || []);
    } catch (err) {
      setError("Failed to load dashboard data.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // ➕ Create Exam
  const handleCreateExam = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      await axios.post(`${API_URL}/api/create_exam`, newExam);
      setNewExam({ title: "", description: "", duration: "" });
      setSuccess("Exam created successfully!");
      fetchDashboardData();
    } catch (err) {
      setError("Error creating exam. Please try again.");
    }
  };

  // 📤 Assign Exam
  const handleAssignExam = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    try {
      await axios.post(`${API_URL}/api/assign_exam`, assignData);
      setAssignData({ studentId: "", examId: "" });
      setSuccess("Exam assigned successfully!");
    } catch (err) {
      setError("Error assigning exam. Please try again.");
    }
  };

  // 🗑️ Delete Exam
  const handleDeleteExam = async (id) => {
    if (!window.confirm("Are you sure you want to delete this exam?")) return;
    try {
      await axios.delete(`${API_URL}/api/exam/${id}`);
      fetchDashboardData();
    } catch {
      setError("Failed to delete exam.");
    }
  };

  // 📘 Exam List
  const renderExamList = () => (
    <div className="space-y-4">
      {exams.map((exam) => (
        <div
          key={exam.id}
          className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center shadow-sm hover:shadow-md transition-all animate-fade-in"
        >
          <div className="flex flex-col">
            <h3 className="text-lg font-semibold text-indigo-700 flex items-center gap-2">
              <BookOpenCheck className="w-5 h-5 text-indigo-600" /> {exam.title}
            </h3>
            <p className="text-sm text-gray-600 mt-1">{exam.description}</p>
            <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
              <span className="flex items-center gap-1">
                <Clock className="w-4 h-4" /> {exam.duration} mins
              </span>
              {exam.scheduled_at && (
                <span className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />{" "}
                  {new Date(exam.scheduled_at).toLocaleString()}
                </span>
              )}
            </div>
          </div>
          <div className="flex gap-3 mt-3 sm:mt-0">
            <button
              onClick={() => handleDeleteExam(exam.id)}
              className="p-2 rounded-lg bg-red-50 text-red-600 hover:bg-red-100 transition"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );

  // 🧾 Create Exam Form
  const renderCreateExamForm = () => (
    <form onSubmit={handleCreateExam} className="space-y-5 animate-fade-in">
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Exam Title
        </label>
        <input
          type="text"
          required
          value={newExam.title}
          onChange={(e) => setNewExam({ ...newExam, title: e.target.value })}
          className="mt-2 w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Description
        </label>
        <textarea
          required
          value={newExam.description}
          onChange={(e) =>
            setNewExam({ ...newExam, description: e.target.value })
          }
          className="mt-2 w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Duration (mins)
        </label>
        <input
          type="number"
          required
          value={newExam.duration}
          onChange={(e) =>
            setNewExam({ ...newExam, duration: e.target.value })
          }
          className="mt-2 w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500"
        />
      </div>
      <button
        type="submit"
        className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-2 rounded-lg font-semibold hover:shadow-md transition"
      >
        Create Exam
      </button>
    </form>
  );

  // 👩‍🏫 Assign Exam Form
  const renderAssignExamForm = () => (
    <form onSubmit={handleAssignExam} className="space-y-5 animate-fade-in">
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Select Student
        </label>
        <select
          required
          value={assignData.studentId}
          onChange={(e) =>
            setAssignData({ ...assignData, studentId: e.target.value })
          }
          className="mt-2 w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">Choose student</option>
          {students.map((s) => (
            <option key={s.id} value={s.id}>
              {s.username}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Select Exam
        </label>
        <select
          required
          value={assignData.examId}
          onChange={(e) =>
            setAssignData({ ...assignData, examId: e.target.value })
          }
          className="mt-2 w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">Choose exam</option>
          {exams.map((e) => (
            <option key={e.id} value={e.id}>
              {e.title}
            </option>
          ))}
        </select>
      </div>
      <button
        type="submit"
        className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-2 rounded-lg font-semibold hover:shadow-md transition"
      >
        Assign Exam
      </button>
    </form>
  );

  // 🌀 Loading
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-white via-slate-50 to-gray-100">
        <Loader2 className="w-10 h-10 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-white via-slate-50 to-gray-100 text-gray-900 font-sans">
      <AdminHeader
        onLogout={() => {
          localStorage.removeItem("proctorUser");
          navigate("/login");
        }}
      />

      <main className="max-w-7xl mx-auto py-10 px-4 sm:px-6 lg:px-8 space-y-8">
        {/* 🌟 Welcome Section */}
        <section className="bg-white border border-gray-200/80 rounded-2xl shadow-lg p-6 sm:p-8 animate-fade-in">
          <div className="flex items-start gap-4">
            <div className="rounded-lg bg-indigo-50 p-3">
              <BookOpen className="w-7 h-7 text-indigo-600" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
                Welcome, <span className="text-indigo-700">Admin</span>
              </h1>
              <p className="mt-1 text-sm text-gray-600">
                Manage exams, assign tests, and oversee student progress.
              </p>
            </div>
          </div>
        </section>

        {/* Navigation Tabs */}
        <div className="flex flex-wrap gap-3">
          <NavTab
            icon={BookOpen}
            label="View Exams"
            isActive={view === "view_exams"}
            onClick={() => setView("view_exams")}
          />
          <NavTab
            icon={PlusCircle}
            label="Create Exam"
            isActive={view === "create_exam"}
            onClick={() => setView("create_exam")}
          />
          <NavTab
            icon={Users}
            label="Assign Exam"
            isActive={view === "assign_exam"}
            onClick={() => setView("assign_exam")}
          />
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center text-red-700 animate-fade-in">
            <AlertTriangle className="w-5 h-5 mr-3" /> {error}
          </div>
        )}
        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-xl flex items-center text-green-700 animate-fade-in">
            <CheckCircle className="w-5 h-5 mr-3" /> {success}
          </div>
        )}

        <section className="bg-white border border-gray-200/80 rounded-2xl shadow-lg p-6 sm:p-10 animate-fade-in">
          {view === "view_exams" && renderExamList()}
          {view === "create_exam" && renderCreateExamForm()}
          {view === "assign_exam" && renderAssignExamForm()}
        </section>
      </main>

      <style jsx>{`
        @keyframes fade-in {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fade-in {
          animation: fade-in 0.5s ease-out forwards;
        }
      `}</style>
    </div>
  );
}

export default AdminDashboard;
