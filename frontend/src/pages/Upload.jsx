import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Upload as UploadIcon, Search, LogOut, DollarSign, CheckCircle2, AlertCircle } from "lucide-react";

function Upload() {
  const navigate = useNavigate();
  const [user, setUser] = useState(localStorage.getItem("user") || null);
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState("");
  const [splitType, setSplitType] = useState('');
  const [customInstruction, setCustomInstruction] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [progress, setProgress] = useState({
    stage: '',
    message: '',
    progress: 0
  });
  
  const [estimatedTime, setEstimatedTime] = useState(null);
  const [startTime, setStartTime] = useState(null);
  const [billId, setBillId] = useState(null);
  
  const wsRef = useRef(null);

  const getInstruction = () => {
    if (splitType === 'custom') {
      return customInstruction || 'Split equally among 2';
    }
    const instructionMap = {
      'equal_2': 'Split equally among 2',
      'equal_3': 'Split equally among 3',
      'equal_4': 'Split equally among 4',
      'equal_5': 'Split equally among 5',
    };
    return instructionMap[splitType] || 'Split equally among 2';
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setFileName(selectedFile.name);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!file) {
      setError('Please select a bill image');
      return;
    }

    if (!splitType) {
      setError('Please select a split option');
      return;
    }

    setLoading(true);
    setStartTime(Date.now());
    setProgress({ stage: 'queuing', message: 'Queuing bill for processing...', progress: 5 });

    const formData = new FormData();
    formData.append('file', file);
    formData.append('instruction', getInstruction());

    try {
      const response = await axios.post('http://localhost:8000/process-bill', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const newBillId = response.data.bill_id;
      setBillId(newBillId);
      connectWebSocket(newBillId);

    } catch (err) {
      setError(err.response?.data?.error || 'Failed to process bill');
      setLoading(false);
      setProgress({ stage: '', message: '', progress: 0 });
    }
  };

  const handleLogout = async () => {
    try {
      const accessToken = localStorage.getItem("access_token");
      
      // Call logout endpoint to invalidate Redis session
      if (accessToken) {
        await axios.post(
          'http://localhost:8000/auth/logout',
          {},
          {
            headers: {
              'Authorization': `Bearer ${accessToken}`
            }
          }
        );
      }
    } catch (error) {
      console.error('Logout error:', error);
      // Continue with logout even if server call fails
    } finally {
      // Clear local storage
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      navigate("/login");
    }
  };

  const connectWebSocket = (billIdParam) => {
    const ws = new WebSocket(`ws://localhost:8000/ws/progress/${billIdParam}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      setProgress({
        stage: data.stage,
        message: data.message,
        progress: data.progress
      });

      if (data.progress > 5 && data.progress < 100) {
        const elapsed = (Date.now() - startTime) / 1000;
        const estimatedTotal = (elapsed / data.progress) * 100;
        const remaining = Math.ceil(estimatedTotal - elapsed);
        setEstimatedTime(remaining > 0 ? remaining : 1);
      }

      if (data.stage === 'completed') {
        setTimeout(() => {
          ws.close();
          navigate(`/result/${billIdParam}`);
        }, 1500);
      }

      if (data.stage === 'error') {
        setError(data.message);
        setLoading(false);
        ws.close();
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('Connection error. Please try again.');
      setLoading(false);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
    };
  };

  const handleRetry = () => {
    setError('');
    setProgress({ stage: '', message: '', progress: 0 });
    setEstimatedTime(null);
    setStartTime(null);
  };

  useEffect(() => {
    const hash = new URLSearchParams(window.location.hash.slice(1));
    const email = hash.get("user_email");
    const name = hash.get("user_name");
    if (email) {
      localStorage.setItem("user", name || email);
      setUser(name || email);
    }
  }, []);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      {/* Top Navigation Bar */}
      <nav className="border-b bg-white/50 dark:bg-gray-900/50 backdrop-blur-xl sticky top-0 z-40">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="h-10 w-10 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center">
                <DollarSign className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
                  PayUp
                </h1>
                {user && (
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    {user}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              {user && (
                <Button 
                  onClick={handleLogout} 
                  variant="ghost"
                  size="sm"
                  className="gap-2"
                >
                  <LogOut className="h-4 w-4" />
                  <span className="hidden sm:inline">Logout</span>
                </Button>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto space-y-6">
          {/* Header */}
          <div className="text-center space-y-2">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white">
              Upload Your Bill
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              Snap a photo or upload an image, and let AI split it for you
            </p>
          </div>

          {/* Upload Card */}
          <Card className="shadow-xl border-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl">
            <CardContent className="p-6 md:p-8">
              {error && (
                <Alert variant="destructive" className="mb-6">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription className="flex items-center justify-between">
                    <span>{error}</span>
                    {billId && (
                      <Button onClick={handleRetry} size="sm" variant="outline">
                        Try Again
                      </Button>
                    )}
                  </AlertDescription>
                </Alert>
              )}
              
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* File Upload */}
                <div className="space-y-2">
                  <Label htmlFor="bill_image" className="text-base font-semibold">
                    Bill Image
                  </Label>
                  <div className="relative">
                    <Input
                      type="file"
                      id="bill_image"
                      accept="image/*"
                      onChange={handleFileChange}
                      required
                      disabled={loading}
                      className="hidden"
                    />
                    <label
                      htmlFor="bill_image"
                      className={`flex flex-col items-center justify-center w-full h-48 border-2 border-dashed rounded-xl cursor-pointer transition-all duration-200 ${
                        file 
                          ? 'border-indigo-600 bg-indigo-50 dark:border-indigo-400 dark:bg-indigo-950/30' 
                          : 'border-gray-300 dark:border-gray-700 hover:border-indigo-400 dark:hover:border-indigo-600 bg-gray-50 dark:bg-gray-800/50'
                      } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <div className="flex flex-col items-center justify-center gap-3 p-6">
                        <div className={`h-16 w-16 rounded-full flex items-center justify-center ${
                          file ? 'bg-indigo-100 dark:bg-indigo-900' : 'bg-gray-100 dark:bg-gray-800'
                        }`}>
                          {file ? (
                            <CheckCircle2 className="h-8 w-8 text-indigo-600 dark:text-indigo-400" />
                          ) : (
                            <UploadIcon className="h-8 w-8 text-gray-400" />
                          )}
                        </div>
                        {file ? (
                          <>
                            <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">
                              {fileName}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              Click to change file
                            </p>
                          </>
                        ) : (
                          <>
                            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                              Drop your bill here or click to browse
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                              PNG, JPG, JPEG up to 10MB
                            </p>
                          </>
                        )}
                      </div>
                    </label>
                  </div>
                </div>
                
                {/* Split Type */}
                <div className="space-y-2">
                  <Label htmlFor="split_type" className="text-base font-semibold">
                    How would you like to split?
                  </Label>
                  <Select 
                    value={splitType} 
                    onValueChange={setSplitType}
                    disabled={loading}
                  >
                    <SelectTrigger className="h-12">
                      <SelectValue placeholder="Choose split option" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="equal_2">Split equally among 2 people</SelectItem>
                      <SelectItem value="equal_3">Split equally among 3 people</SelectItem>
                      <SelectItem value="equal_4">Split equally among 4 people</SelectItem>
                      <SelectItem value="equal_5">Split equally among 5 people</SelectItem>
                      <SelectItem value="custom">Custom instruction</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Custom Instruction */}
                {splitType === 'custom' && (
                  <div className="space-y-2">
                    <Label htmlFor="custom_instruction" className="text-base font-semibold">
                      Custom Split Instructions
                    </Label>
                    <Input
                      type="text"
                      id="custom_instruction"
                      value={customInstruction}
                      onChange={(e) => setCustomInstruction(e.target.value)}
                      placeholder="e.g., Person A pays 60%, Person B pays 40%"
                      disabled={loading}
                      className="h-12"
                    />
                  </div>
                )}
                
                {/* Submit Button */}
                <Button 
                  type="submit" 
                  className="w-full h-12 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-semibold text-base shadow-lg shadow-indigo-500/30 dark:shadow-indigo-500/20"
                  disabled={loading}
                  size="lg"
                >
                  {loading ? (
                    <>
                      <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <UploadIcon className="h-5 w-5 mr-2" />
                      Process Bill
                    </>
                  )}
                </Button>
              </form>
              
              {/* Divider */}
              <div className="relative my-8">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t border-gray-200 dark:border-gray-700" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-white dark:bg-gray-900 px-2 text-gray-500 dark:text-gray-400">
                    Or
                  </span>
                </div>
              </div>
              
              {/* Lookup Button */}
              <Button
                onClick={() => navigate('/lookup')}
                variant="outline"
                className="w-full h-12 font-semibold"
                disabled={loading}
                size="lg"
              >
                <Search className="h-5 w-5 mr-2" />
                Lookup Existing Bill
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Processing Overlay - Same as before */}
      {loading && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-lg shadow-2xl border-0">
            <CardContent className="p-8">
              {progress.stage === 'completed' ? (
                <div className="text-center space-y-6">
                  <div className="mx-auto h-20 w-20 rounded-full bg-green-100 dark:bg-green-950 flex items-center justify-center animate-scale-in">
                    <CheckCircle2 className="h-12 w-12 text-green-600 dark:text-green-400" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
                      Success!
                    </h3>
                    <p className="text-gray-600 dark:text-gray-400">
                      Your bill has been split successfully
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-8">
                  <div className="flex justify-center">
                    <div className="h-16 w-16 rounded-full border-4 border-gray-200 dark:border-gray-700 border-t-indigo-600 dark:border-t-indigo-400 animate-spin" />
                  </div>
                  
                  <div className="space-y-4">
                    <h2 className="text-2xl font-bold text-center text-gray-900 dark:text-white">
                      Processing Your Bill
                    </h2>
                    
                    <div className="space-y-3">
                      <Progress value={progress.progress} className="h-3" />
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
                          {progress.progress}%
                        </span>
                        {estimatedTime && progress.progress < 95 && (
                          <span className="text-gray-600 dark:text-gray-400 font-medium animate-pulse">
                            ~{estimatedTime}s remaining
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="space-y-3">
                    {[
                      { stage: 'uploading', icon: '📤', label: 'Uploading bill...', threshold: 30 },
                      { stage: 'ocr', icon: '🔍', label: 'Extracting text...', threshold: 50 },
                      { stage: 'splitting', icon: '💰', label: 'Calculating splits...', threshold: 80 },
                      { stage: 'saving', icon: '💾', label: 'Saving results...', threshold: 95 },
                      { stage: 'completed', icon: '✅', label: 'Complete!', threshold: 100 }
                    ].map((step) => (
                      <div
                        key={step.stage}
                        className={`flex items-center gap-4 p-4 rounded-xl transition-all duration-300 ${
                          progress.stage === step.stage
                            ? 'bg-indigo-50 dark:bg-indigo-950/30 border-l-4 border-indigo-600 dark:border-indigo-400 shadow-md animate-pulse-glow'
                            : progress.progress >= step.threshold
                            ? 'bg-green-50 dark:bg-green-950/20 opacity-75'
                            : 'bg-gray-50 dark:bg-gray-800/30 opacity-50'
                        }`}
                      >
                        <div className={`h-12 w-12 rounded-full flex items-center justify-center text-2xl ${
                          progress.stage === step.stage
                            ? 'bg-white dark:bg-gray-900 shadow-md'
                            : ''
                        }`}>
                          {step.icon}
                        </div>
                        <div className="flex-1">
                          <p className={`font-medium ${
                            progress.stage === step.stage
                              ? 'text-gray-900 dark:text-white'
                              : 'text-gray-600 dark:text-gray-400'
                          }`}>
                            {progress.stage === step.stage ? progress.message : step.label}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

export default Upload;