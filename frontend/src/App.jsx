import "bootstrap/dist/css/bootstrap.min.css";
import { Route, HashRouter as Router, Routes } from "react-router-dom";
import Accommodation from "./components/Accommodation/Accommodation";
import AdminPanel from "./components/AdminPanel/AdminPanel";

import Container from "./components/Container/Container";
import EditParticipants from "./components/EditParticipants/EditParticipants";
import EditProgram from "./components/EditProgram/EditProgram";
import EditProgramInfo from "./components/EditProgramInfo/EditProgramInfo";
import EditWebInfo from "./components/EditWebInfo/EditWebInfo";
import EditWebInfoAccommodation from "./components/EditWebInfoAccommodation/EditWebInfoAccommodation";
import EditWebInfoFooter from "./components/EditWebInfoFooter/EditWebInfoFooter";
import EditWebInfoHiking from "./components/EditWebInfoHiking/EditWebInfoHiking";
import EditWebInfoHome from "./components/EditWebInfoHome/EditWebInfoHome";
import EditWebInfoRegistration from "./components/EditWebInfoRegistration/EditWebInfoRegistration";
import EditWebInfoVenue from "./components/EditWebInfoVenue/EditWebInfoVenue";
import Footer from "./components/Footer/Footer";
import Header from "./components/Header/Header";
import Hiking from "./components/Hiking/Hiking";
import Landing from "./components/Landing/Landing";
import ParticipantsInfo from "./components/ParticipantsInfo/ParticipantsInfo";
import ProtectedRoute from "./components/ProtectedRoute/ProtectedRoute";
import { useConferenceExists } from "./components/hooks/useConferenceExists";
import Loader from "./components/ui/Loader/Loader";
import ScrollToTop from "./components/ui/ScrollToTop";
import Venue from "./components/Venue/Venue";
import AbstractsPage from "./pages/AbstractsPage";
import HomePage from "./pages/HomePage";
import Participants from "./pages/ParticipantsPage";
import ProgramPage from "./pages/ProgramPage";
import RegistrationPage from "./pages/RegistrationPage";

function App() {
  const conferenceState = useConferenceExists();

  // Landing renders bare — conference chrome is per-conference only.
  // A path slug that matches no real conference ALSO renders the landing
  // page: every scoped API call would 404 and the component fallbacks
  // would otherwise fake a "ghost" conference.
  if (conferenceState === "landing" || conferenceState === "missing") {
    return <Landing />;
  }

  if (conferenceState === "checking") {
    return <Loader />;
  }

  return (
    <Router>
      <ScrollToTop />
      <Container>
        <Header />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/participants" element={<Participants />} />
          <Route path="/abstracts" element={<AbstractsPage />} />
          <Route path="/registration" element={<RegistrationPage />} />
          <Route path="/program" element={<ProgramPage />} />
          <Route path="/venue" element={<Venue />} />
          <Route path="/accommodation" element={<Accommodation />} />
          <Route path="/hiking" element={<Hiking />} />
          {/* Protected Admin Routes */}
          <Route
            path="/admin-panel"
            element={
              <ProtectedRoute>
                <AdminPanel />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin-panel/participants-info"
            element={
              <ProtectedRoute>
                <ParticipantsInfo />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin-panel/edit-participants"
            element={
              <ProtectedRoute>
                <EditParticipants />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin-panel/edit-program"
            element={
              <ProtectedRoute>
                <EditProgram />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin-panel/edit-program/info"
            element={
              <ProtectedRoute>
                <EditProgramInfo />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin-panel/edit-web-info"
            element={
              <ProtectedRoute>
                <EditWebInfo />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin-panel/edit-web-info/home"
            element={
              <ProtectedRoute>
                <EditWebInfoHome />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin-panel/edit-web-info/registration"
            element={
              <ProtectedRoute>
                <EditWebInfoRegistration />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin-panel/edit-web-info/venue"
            element={
              <ProtectedRoute>
                <EditWebInfoVenue />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin-panel/edit-web-info/accommodation"
            element={
              <ProtectedRoute>
                <EditWebInfoAccommodation />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin-panel/edit-web-info/hiking"
            element={
              <ProtectedRoute>
                <EditWebInfoHiking />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin-panel/edit-web-info/footer"
            element={
              <ProtectedRoute>
                <EditWebInfoFooter />
              </ProtectedRoute>
            }
          />
        </Routes>
        <Footer />
      </Container>
    </Router>
  );
}

export default App;
