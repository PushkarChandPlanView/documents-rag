import styled from "styled-components";
import SearchLanding from "../../../assets/images/search-landing-slate.svg";
import SearchTip from "../../../assets/images/search-tips-lightbulb.svg";

type Props = {};
const Landing = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`;

const Title = styled.div`
  font-weight: 600;
  color: #202124;
  margin-bottom: 1rem;
`;

const Tips = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
`;

const TipImage = styled.img`
  width: 36px;
  height: 36px;
`;

const TipContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-direction: column;
`;

const TipTitle = styled.div`
  font-weight: 500;
  color: #202124;
`;

const Tip = styled.div`
  font-size: 0.8rem;
  color: #555;
`;

const LandingPage = (_props: Props) => {
  return (
    <Landing>
      <Title>Start typing at least 3 letters to see results</Title>
      <img src={SearchLanding} alt="Search landing" />
      <TipContainer>
        <TipImage src={SearchTip} alt="Search tip" />
        <TipTitle>Search Tips</TipTitle>
      </TipContainer>
      <Tips>
        <Tip>Use quotes to search for exact phrases.</Tip>
        <Tip>Try different keywords to improve your search.</Tip>
      </Tips>
    </Landing>
  );
};

export default LandingPage;
