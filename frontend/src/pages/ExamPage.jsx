import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import Header from '../components/Header'; // We'll reuse the header

// --- Configuration ---
// Make sure this points to your *correct* deployed backend URL or localhost
// const API_URL = 'https://proctorai-plus-backend.vercel.app'; // Example Vercel URL
const API_URL = 'https://proctorai-plus-1.onrender.com'; // Example Render URL
// const API_URL = 'http://127.0.0.1:5000'; // For local testing
const CLIENT_EXECUTABLE_NAME = "ProctorAI.exe"; // Name of the file in /public
// --- End Configuration ---

function ExamPage() {
    const [user, setUser] = useState(null);
    const [exam, setExam] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [examStarted, setExamStarted] = useState(false);
    const { examId } = useParams();
    const navigate = useNavigate();
    const sessionIdRef = useRef(null);
    const userRef = useRef(null);

    // 1. Get user from localStorage
    useEffect(() => {
        const storedUser = JSON.parse(localStorage.getItem('proctorUser'));
        if (storedUser) {
            setUser(storedUser);
            userRef.current = storedUser;
        } else {
            navigate('/login');
        }
    }, [navigate]);

    // 2. Fetch exam details (depend on user being loaded)
    useEffect(() => {
        if (!examId || !user) {
            if (user) setLoading(false); // User loaded, but no examId? Stop loading.
            return; // Don't fetch if user or examId isn't ready
        }
        const fetchExamDetails = async () => {
            setLoading(true);
            setError('');
            try {
                const response = await axios.get(`${API_URL}/api/exam_details/${examId}`);
                setExam(response.data);
            } catch (err) {
                console.error("Error fetching exam details:", err);
                setError(`Failed to load exam details (ID: ${examId}). Please check the ID or contact support.`);
            } finally {
                setLoading(false);
            }
        };
        fetchExamDetails();
    }, [examId, user]); // Re-run if examId or user changes

    // 3. Tab Switching Detection (Visibility API only)
    useEffect(() => {
        const handleVisibilityChange = () => {
            if (document.hidden) {
                console.log('User switched tabs or minimized');
                sendWebAlert('WEB: Switched tabs');
            }
        };
        if (examStarted) {
            document.addEventListener('visibilitychange', handleVisibilityChange);
        }
        return () => { // Cleanup
            document.removeEventListener('visibilitychange', handleVisibilityChange);
        };
    }, [examStarted]);

    // Helper to send web alerts
    const sendWebAlert = async (alertMessage) => {
        if (!userRef.current || !sessionIdRef.current) return;
        const payload = { source: 'web', student_id: userRef.current.username, session_id: sessionIdRef.current, alerts: [alertMessage] };
        try { await axios.post(`${API_URL}/log_data`, payload); }
        catch (err) { console.error('Failed to send web alert:', err); }
    };

    // Handle starting the exam (sets state, generates session ID)
    const handleStartExam = () => {
        if (!user || !examId) return;
        const timestamp = new Date().toISOString().replace(/[-:.]/g, '');
        sessionIdRef.current = `exam_${examId}_${user.username}_${timestamp}`; // Z is included
        console.log('Exam started. Session ID:', sessionIdRef.current);
        setExamStarted(true);
    };

    // --- Render Logic ---

    // Loading State
    if (loading || !user) {
        return ( <div className="min-h-screen bg-gray-100 flex items-center justify-center"><p className="text-lg font-semibold text-indigo-600 animate-pulse">Loading Exam...</p></div> );
    }

    // Error State
    if (error) {
        return (
            <div className="min-h-screen bg-gray-100">
                <Header username={user?.username || 'Student'} portalType="Student" />
                <div className="max-w-xl mx-auto py-12 px-4 text-center">
                    <h2 className="text-2xl font-bold text-red-600 mb-4">⚠️ Error Loading Exam</h2>
                    <p className="text-gray-700 bg-red-50 p-4 rounded border border-red-200">{error}</p>
                    <button onClick={() => navigate('/student/dashboard')} className="mt-6 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">Back to Dashboard</button>
                </div>
            </div>
        );
    }

    // == Pre-Exam Instructions View ==
    if (!examStarted) {
        const downloadLink = `https://github.com/vishwas2222/ProctorAI-Plus/releases/download/v1.0.0/ProctorAI.exe`; // Assumes file is in /public
        const runCommand = `.\\${CLIENT_EXECUTABLE_NAME} --username ${user.username} --exam_id ${examId}`;
        // macOS/Linux alternative command (adjust executable name if needed)
        const runCommandMacLinux = `./${CLIENT_EXECUTABLE_NAME.replace('.exe', '')} --username ${user.username} --exam_id ${examId}`;

        return (
            <div className="min-h-screen bg-gray-100">
                <Header username={user.username} portalType="Student" />
                <div className="max-w-4xl mx-auto py-10 px-4 sm:px-6 lg:px-8">
                    <div className="bg-white p-8 rounded-2xl shadow-xl space-y-6">
                        {/* Exam Title & Desc */}
                        <div className="text-center border-b pb-4">
                            <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">{exam?.title}</h1>
                            {exam?.description && <p className="mt-2 text-lg text-gray-600">{exam?.description}</p>}
                        </div>

                        {/* Rules & Requirements */}
                        <div>
                           <h2 className="text-xl font-bold text-indigo-700 mb-3">📜 Exam Rules & Requirements</h2>
                           <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded-r-lg text-yellow-800 space-y-2 text-sm">
                               <p><strong><span className="text-red-600">*</span> Strict Proctoring is Active:</strong> Your session will be monitored.</p>
                               <ul className="list-disc list-inside ml-4">
                                   <li>Be alone in a quiet room.</li>
                                   <li>Keep your face clearly visible to the webcam at all times.</li>
                                   <li>No external aids (phones, books, websites, other people).</li>
                                   <li>**Do not switch browser tabs or minimize this window.**</li>
                                   <li>Ensure only your face is visible on camera (no multiple faces).</li>
                               </ul>
                               <p>Violations will be flagged and reported.</p>
                           </div>
                        </div>

                        {/* Setup Instructions */}
                        <div>
                            <h2 className="text-xl font-bold text-indigo-700 mb-3">⚙️ Setup Instructions</h2>
                            <div className="space-y-4 text-sm text-gray-700">
                                <div className="p-4 bg-gray-50 rounded-lg border">
                                    <p className="font-semibold">1. Download Proctoring Client:</p>
                                    <p className="mb-2">If you haven't already, download the required software:</p>
                                    <a
                                        href={downloadLink}
                                        download
                                        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                                    >
                                        <svg className="-ml-1 mr-2 h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
                                        Download {CLIENT_EXECUTABLE_NAME}
                                    </a>
                                    <p className="text-xs text-gray-500 mt-1">Save it somewhere easy to find (e.g., Desktop).</p>
                                </div>

                                <div className="p-4 bg-gray-50 rounded-lg border">
                                     <p className="font-semibold">2. Open Terminal / Command Prompt:</p>
                                     <ul className="list-disc list-inside ml-4 text-xs text-gray-600">
                                         <li><b>Windows:</b> Search for "Command Prompt" or "PowerShell".</li>
                                         <li><b>macOS/Linux:</b> Open "Terminal".</li>
                                     </ul>
                                     <p className="mt-1">Use the `cd` command to navigate to where you saved the file (e.g., `cd Desktop`).</p>
                                </div>

                                <div className="p-4 bg-gray-50 rounded-lg border">
                                    <p className="font-semibold">3. Run the Client:</p>
                                    <p>Copy and paste the exact command below into your terminal and press Enter:</p>
                                    <pre className="bg-gray-800 text-green-300 rounded-md p-3 my-2 overflow-x-auto text-xs font-mono select-all">
                                        {runCommand}
                                    </pre>
                                     <p className="text-xs text-gray-500">(On macOS/Linux, use: <code className="bg-gray-200 text-xs px-1 rounded">{runCommandMacLinux}</code>)</p>
                                </div>

                                <div className="p-4 bg-gray-50 rounded-lg border">
                                    <p className="font-semibold">4. Wait for Calibration:</p>
                                    <p>A window with your webcam feed will appear. Wait until the terminal shows <code className="bg-gray-200 text-xs px-1 rounded">[✅] Calibration complete...</code> and <code className="bg-gray-200 text-xs px-1 rounded">[🎥] Camera started...</code>. <strong className="text-red-600">Do NOT close this window.</strong></p>
                                </div>
                            </div>
                        </div>

                        {/* Start Button */}
                        <div className="pt-5 text-center">
                             <button
                                onClick={handleStartExam}
                                className="w-full sm:w-auto inline-flex justify-center py-3 px-8 border border-transparent shadow-lg text-lg font-bold rounded-full text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition duration-150 ease-in-out disabled:opacity-50 disabled:cursor-not-allowed"
                                disabled={!exam}
                            >
                                ✅ I have launched the client. Start Exam Now.
                            </button>
                            {!exam && <p className="text-xs text-red-500 mt-2">Waiting for exam details before starting...</p>}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // == Live Exam View == (Unchanged - Placeholder content)
    return (
        <div className="min-h-screen bg-gray-100">
             <Header username={user.username} portalType="Student" />
             <div className="max-w-5xl mx-auto py-12 px-4">
                 <div className="bg-white p-8 rounded-lg shadow-xl">
                     <div className="flex justify-between items-center mb-6 pb-4 border-b">
                         <h1 className="text-3xl font-bold text-gray-900">{exam?.title}</h1>
                         <span className="flex items-center px-3 py-1 bg-red-100 text-red-800 font-medium rounded-full text-sm">
                             <svg className="w-4 h-4 mr-1 animate-pulse" fill="currentColor" viewBox="0 0 8 8"><circle cx="4" cy="4" r="3"></circle></svg>
                             PROCTORING ACTIVE
                         </span>
                     </div>

                     {/* Placeholder Exam Content */}
                     <div className="space-y-8 border p-6 rounded-lg bg-gray-50 shadow-inner">
                         {/* Question 1 */}
                         <div>
                             <h2 className="text-lg font-semibold text-gray-800 mb-2">Question 1</h2>
                             <p className="text-gray-700 mb-3">What is the primary function of a mitochondria?</p>
                             <div className="space-y-2 pl-4">
                                 <label className="flex items-center cursor-pointer p-2 rounded hover:bg-indigo-50 transition duration-150"><input type="radio" name="q1" className="mr-3 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"/> The powerhouse of the cell.</label>
                                 <label className="flex items-center cursor-pointer p-2 rounded hover:bg-indigo-50 transition duration-150"><input type="radio" name="q1" className="mr-3 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"/> To store water.</label>
                                 <label className="flex items-center cursor-pointer p-2 rounded hover:bg-indigo-50 transition duration-150"><input type="radio" name="q1" className="mr-3 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"/> To perform photosynthesis.</label>
                             </div>
                         </div>

                         {/* Question 2 */}
                         <div>
                             <h2 className="text-lg font-semibold text-gray-800 mb-2">Question 2</h2>
                             <p className="text-gray-700 mb-3">What is React?</p>
                             <textarea className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm placeholder-gray-400" rows="5" placeholder="Explain React in your own words..."></textarea>
                         </div>
                     </div>
                     {/* End Placeholder */}

                     <div className="mt-10 text-center">
                         <button
                            onClick={() => {
                                alert('Exam submitted! Proctoring data has been saved.');
                                // You might want to send a final event: sendWebAlert("Exam Finished");
                                navigate('/student/dashboard');
                            }}
                            className="w-full sm:w-auto inline-flex justify-center py-3 px-10 border border-transparent shadow-lg text-lg font-bold rounded-full text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 ease-in-out"
                        >
                            Submit Exam
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default ExamPage;