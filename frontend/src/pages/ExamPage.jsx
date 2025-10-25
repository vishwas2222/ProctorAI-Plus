import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import Header from '../components/Header'; // We'll reuse the header

const API_URL = 'http://127.0.0.1:5000';

function ExamPage() {
  const [user, setUser] = useState(null);
  const [exam, setExam] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [examStarted, setExamStarted] = useState(false);
  const { examId } = useParams(); // Get examId from URL
  const navigate = useNavigate();

  // Ref to store the session ID once generated
  const sessionIdRef = useRef(null);
  // Ref to store the user
  const userRef = useRef(null);

  // 1. Get user from localStorage
  useEffect(() => {
    const storedUser = JSON.parse(localStorage.getItem('proctorUser'));
    if (storedUser) {
      setUser(storedUser);
      userRef.current = storedUser; // Store in ref for event listeners
    } else {
      navigate('/login'); // Not logged in, kick to login
    }
  }, [navigate]);

  // 2. Fetch exam details
  useEffect(() => {
    if (!examId) return;
    const fetchExamDetails = async () => {
      setLoading(true);
      setError('');
      try {
        const response = await axios.get(`${API_URL}/api/exam_details/${examId}`);
        setExam(response.data);
      } catch (err) {
        setError('Failed to load exam details. Does this exam exist?');
      } finally {
        setLoading(false);
      }
    };
    fetchExamDetails();
  }, [examId]);

  // 3. ✨ Tab Switching & Focus Detection ✨
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // User switched tabs or minimized
        console.log('User switched tabs');
        sendWebAlert('WEB: Switched tabs');
      }
    };

    const handleBlur = () => {
      // User clicked outside the window (e.g., on desktop)
      console.log('User left focus');
      sendWebAlert('WEB: Left focus');
    };

    // Only add listeners if the exam has started
    if (examStarted) {
      document.addEventListener('visibilitychange', handleVisibilityChange);
      window.addEventListener('blur', handleBlur);
    }

    // Cleanup function
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('blur', handleBlur);
    };
  }, [examStarted]); // Dependency: only run when examStarted changes

  // Helper function to send web-based alerts
  const sendWebAlert = async (alertMessage) => {
    // Check if user and session are valid
    if (!userRef.current || !sessionIdRef.current) {
      console.warn('Cannot send web alert: user or session ID is missing.');
      return;
    }

    const payload = {
      source: 'web',
      student_id: userRef.current.username, // Send username
      session_id: sessionIdRef.current,
      alerts: [alertMessage]
    };

    try {
      await axios.post(`${API_URL}/log_data`, payload);
    } catch (err) {
      console.error('Failed to send web alert:', err);
    }
  };

  const handleStartExam = () => {
    // Generate the unique session ID
    // We remove special chars from timestamp for a cleaner ID
    const timestamp = new Date().toISOString().replace(/[-:.]/g, '');
    sessionIdRef.current = `exam_${examId}_${user.username}_${timestamp}`;
    
    console.log('Exam started. Session ID:', sessionIdRef.current);
    setExamStarted(true);
  };

  // --- Render Logic ---

  if (loading || !user) {
    return <div className="min-h-screen bg-gray-100 flex items-center justify-center">Loading...</div>;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100">
        <Header username={user?.username || 'Student'} portalType="Student" />
        <div className="max-w-xl mx-auto py-12 px-4 text-center">
          <h2 className="text-2xl font-bold text-red-600 mb-4">Error</h2>
          <p className="text-gray-700">{error}</p>
          <button
            onClick={() => navigate('/student/dashboard')}
            className="mt-6 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  // == Show Pre-Exam Instructions ==
  if (!examStarted) {
    return (
      <div className="min-h-screen bg-gray-100">
        <Header username={user.username} portalType="Student" />
        <div className="max-w-3xl mx-auto py-12 px-4">
          <div className="bg-white p-8 rounded-lg shadow-lg">
            <h1 className="text-3xl font-bold mb-2 text-gray-900">{exam?.title}</h1>
            <p className="text-lg text-gray-600 mb-6">{exam?.description}</p>
            
            <h2 className="text-2xl font-bold mb-4 text-indigo-700">Exam Instructions</h2>
            
            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6">
              <h3 className="font-bold text-yellow-800">ACTION REQUIRED: Launch Proctoring</h3>
              <p className="text-yellow-700">
                You must launch the **ProctorAI+ Client Agent** to take this exam.
              </p>
            </div>
            
            <ol className="list-decimal list-inside space-y-4 text-gray-700">
              <li>
                <strong>Launch the Client:</strong> Open the `ProctorAI-Client` application on your computer.
                (This is the `main.py` script).
              </li>
              <li>
                <strong>Run with Parameters:</strong> You must launch it from your terminal with the following command:
                <pre className="bg-gray-800 text-white rounded-md p-3 my-2 overflow-x-auto">
                  python main.py --username {user.username} --exam_id {examId}
                </pre>
              </li>
              <li>
                <strong>Calibration:</strong> The client will open, show your camera, and run a 
                brief calibration. Do not close this window.
              </li>
              <li>
                <strong>Stay Focused:</strong> Once you click "Start Exam," you must not switch tabs, 
                leave the window, or allow others into the room.
              </li>
            </ol>

            <button
              onClick={handleStartExam}
              className="mt-8 w-full py-3 px-4 bg-green-600 text-white font-bold rounded-lg text-xl hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
            >
              I have launched the client. Start Exam.
            </button>
          </div>
        </div>
      </div>
    );
  }

  // == Show Live Exam ==
  return (
    <div className="min-h-screen bg-gray-100">
      <Header username={user.username} portalType="Student" />
      <div className="max-w-5xl mx-auto py-12 px-4">
        <div className="bg-white p-8 rounded-lg shadow-lg">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-3xl font-bold text-gray-900">{exam?.title}</h1>
            <span className="px-3 py-1 bg-red-100 text-red-800 font-medium rounded-full text-sm">
              <span className="animate-pulse">●</span> PROCTORING ACTIVE
            </span>
          </div>
          
          {/* Placeholder for Exam Content */}
          <div className="space-y-6">
            <h2 className="text-xl font-semibold">Question 1</h2>
            <p>What is the primary function of a mitochondria?</p>
            <div className="space-y-2">
              <label className="flex items-center"><input type="radio" name="q1" className="mr-2"/> The powerhouse of the cell.</label>
              <label className="flex items-center"><input type="radio" name="q1" className="mr-2"/> To store water.</label>
              <label className="flex items-center"><input type="radio" name="q1" className="mr-2"/> To perform photosynthesis.</label>
            </div>

            <hr className="my-6"/>

            <h2 className="text-xl font-semibold">Question 2</h2>
            <p>What is React?</p>
            <textarea className="mt-2 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm" rows="4" placeholder="Your answer..."></textarea>
          </div>
          {/* End Placeholder */}

          <button
            onClick={() => {
              alert('Exam submitted!');
              navigate('/student/dashboard');
            }}
            className="mt-10 w-full py-3 px-4 bg-indigo-600 text-white font-bold rounded-lg text-lg hover:bg-indigo-700"
          >
            Submit Exam
          </button>
        </div>
      </div>
    </div>
  );
}

export default ExamPage;